import vertexai
from vertexai.generative_models import GenerativeModel
from google.cloud.aiplatform.private_preview.vertex_agents_v2 import agents, sessions
import json
from vertexai.preview.vision_models import ImageGenerationModel
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
import time
import base64

import gradio as gr
import logging

logging.basicConfig(filename='presentation_generation.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


PROJECT_ID = "<your-project-id>" 
LOCATION = "us-central1" 
vertexai.init(project=PROJECT_ID, location=LOCATION)

 
MODEL = "gemini-1.5-pro-001"
IMAGE_MODEL = "imagen-3.0-generate-001"

# Initialize agents
story_generator = GenerativeModel(MODEL, system_instruction=["You are a helpful story writer and an expert on any given topic.Do not ask clarifiying questions."])
slide_generator_app = agents.create(display_name="Slide Generator",model=MODEL, instruction="You create clear, concise slide decks.  Each slide has a title, a short paragraph (max 3 sentences), and bullet points(A MUST have). Separate slides with '=== slide ==='.")
slide_refiner_app = agents.create(display_name="Slide Refiner", model=MODEL,instruction="You are a slide deck expert, specializing in creating clear, concise, and engaging presentations.  Your task is to review and improve the provided slide deck. For each slide in the deck, carefully analyze the title, description, and key takeaways.  Suggest changes that enhance clarity, conciseness, and audience engagement.  If a slide effectively communicates its message and does not require improvement, leave the text as is. You MUST return the FULL revised slide deck, including ALL original slides, even if unchanged. Separate slides with '=== slide ==='.")
image_description_app = agents.create(display_name="Image Descriptions", model=MODEL,instruction="You generate evocative image descriptions for slides, capturing the essence of the content and era.Suitable for a watercolor illustration.")

json_converter_app = agents.create(display_name="JSON Converter", model=MODEL,instruction="""Convert slide text to JSON: ```json
[
  { 
    "title": "<title>",
    "description": "<description>",
    "takeaways": ["<takeaway 1>", "<takeaway 2>", "<takeaway 3>"]
  }, ...
]
```""")
imagen_model = ImageGenerationModel.from_pretrained(IMAGE_MODEL)


pdf_file = "slides.pdf"
def generate_presentation(query: str, num_refinement_rounds: int = 2, progress=gr.Progress()):
    """Generates a presentation based on a query."""
    try:
        progress(0, desc="Generating story...")
        story = story_generator.generate_content(query, generation_config={"max_output_tokens": 8192}).text
        logging.info(f"Generated story: {story}")


        progress(0.1, desc="Generating initial slides...")
        slide_generator_session = sessions.create() 
        time.sleep(1)
        slides = slide_generator_session.create_run(agent=slide_generator_app, content=f"Write a slide deck for:\n{story}").steps[-1].content.parts[0].text
        logging.info(f"Generated initial slides: {slides}")



        progress(0.2, desc="Refining slides...")
        
        for i in range(num_refinement_rounds):
            slide_refiner_session = sessions.create()
            time.sleep(1)
            refinement_suggestions = slide_refiner_session.create_run(agent=slide_refiner_app, content=slides).steps[-1].content.parts[0].text
            slides = refinement_suggestions  
            progress(0.2 + (i + 1) * 0.1 / num_refinement_rounds, desc=f"Refining slides (round {i+1}/{num_refinement_rounds})")
            logging.info(f"Refinement suggestions for round {i+1}: {refinement_suggestions}")



        progress(0.3, desc="Converting to JSON...")
        json_converter_session = sessions.create() 
        time.sleep(1)
        slides_json = json_converter_session.create_run(agent=json_converter_app, content=slides).steps[-1].content.parts[0].text


        # JSON handling
        try:
            cleaned_json_string = slides_json.replace("```json", "").replace("```", "").strip()
            slide_data = json.loads(cleaned_json_string)
            logging.info(f"Generated JSON: {cleaned_json_string}") 

        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error: {e}")
            logging.error(f"Raw JSON string: {slides_json}") 
            return "Error: Invalid JSON generated."

        progress(0.4, desc="Generating image descriptions and images...")
        image_description_session = sessions.create() 
        time.sleep(1)
        slide_data_with_images = generate_images(slide_data, image_description_session, imagen_model, query, progress)

        progress(0.9, desc="Creating PDF...")
        create_pdf(slide_data_with_images, pdf_file)

        progress(1, desc="Done!")
        
        # delete sessions.
        slide_generator_session.delete()
        slide_refiner_session.delete()
        json_converter_session.delete()
        image_description_session.delete()

        return gr.File(pdf_file)

    except Exception as e:
        logging.exception(f"An unexpected error occurred: {e}")  
        return f"An error occurred: {e}"

# All the fancy code for the progress bars is suggested by Gemini

def generate_images(slide_data, image_description_session, image_model, query, progress=gr.Progress()):
    """Generates images for each slide."""
    total_slides = len(slide_data)
    import random
    r = random.randint(100,500000)
    logging.info(f"Random seed: {r}")
    for i, d in enumerate(slide_data):
        while True: 
            try:
                prompt = image_description_session.create_run(agent=image_description_app,
                    content=f"Topic: {query}.\n Slide title: {d.get('title', '')} \n Slide main message: {d.get('description', '')} \n Slide bullet points: {d.get('takeaways', [])}"
                ).steps[-1].content.parts[0].text

                response = image_model.generate_images(
                    prompt=prompt, aspect_ratio="1:1" ,number_of_images=1,
                    negative_prompt="blurry and deformed",
                    seed=r,
                    add_watermark=False,
                )


                if response.images: 
                   slide_data[i]['image'] = response.images[0]._as_base64_string()
                   logging.info(f"Generated image for slide {i+1} with prompt: {prompt}")
                   break 
                else:
                   logging.warning(f"No image generated for prompt: {prompt}. Retrying...")
                   time.sleep(1) 

            except Exception as e:
                logging.error(f"Image generation error: {e}. Retrying...")
                time.sleep(1) 
        progress(0.4 + (i + 1) * 0.5 / total_slides, desc=f"Generating image {i+1}/{total_slides}") 
    return slide_data

def create_pdf(slide_data, pdf_file):
    """Creates a PDF from slide data."""
    doc = SimpleDocTemplate(pdf_file, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    first_page = True  # Flag to track the first page

    for slide in slide_data:
        title = slide.get('title', '')
        description = slide.get('description', '')
        takeaways = slide.get('takeaways', [])
        image_data = slide.get('image')

        # Add page break before each title EXCEPT for the first page
        if not first_page:
            story.append(PageBreak())
        else:
            first_page = False 

        if title:
            story.append(Paragraph(title, styles['h1']))
            story.append(Spacer(1, 12))

        if image_data:
            try:
                image_data = BytesIO(base64.b64decode(image_data))
                img = Image(image_data, width=400, height=300)
                story.append(img)
                story.append(Spacer(1, 12))
            except Exception as e:
                logging.error(f"Error adding image to PDF: {e}")

        if description:
            story.append(Paragraph(description, styles['Normal']))
            story.append(Spacer(1, 12))

        for takeaway in takeaways:
            story.append(Paragraph(f"- {takeaway}", styles['Normal']))
        story.append(Spacer(1, 24))

    doc.build(story)

    return pdf_file


def gradio_generate_presentation(query, num_refinement_rounds=2, progress=gr.Progress()):
    return generate_presentation(query, num_refinement_rounds, progress)

with gr.Blocks() as demo:
    gr.Markdown("# Presento: AI Presentation Maker")
    gr.HTML("""<br>""")
    with gr.Row():
        with gr.Column():
            query_input = gr.Textbox(label="Presentation Topic", placeholder="Enter your topic here, eg. using Generative AI to write unit test cases")
            refinement_rounds_input = gr.Slider(minimum=1, maximum=3, step=1, value=1, label="Refinement Rounds")
            submit_button = gr.Button("Generate Presentation")

        with gr.Column():
            pdf_download = gr.File(label="Download Presentation", visible=True) 

    
    gr.Markdown("### [Code Repository](https://github.com/krishnaji/presento)")
    gr.Markdown("### [Sample Presentation](https://github.com/krishnaji/sample-files/blob/main/GenAIUnittest.pdf)")


    submit_button.click(
        fn=gradio_generate_presentation,
        inputs=[query_input, refinement_rounds_input],
        outputs=[pdf_download]
    )
demo.queue(default_concurrency_limit=10)
demo.launch(server_name="0.0.0.0", server_port=8080)