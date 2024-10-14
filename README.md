# Presento: AI Presentation Maker

## Overview

This application leverages the power of Vertex AI Agents API and the Imagen text-to-image model, to generate presentations based on a user-provided topic. 

![](Learn2Learn.gif)

## Features

* **Vertex Agents for Content Creation:**  
    * **Story Generation:** Creates a comprehensive story related to the user's topic.
    * **Slide Generation:** Structures the story into a basic slide deck format.
    * **Slide Refinement:** Iteratively improves the slide deck's clarity, conciseness, and engagement.
    * **Image Description Generation:** Creates detailed prompts for image generation tailored to each slide's content.
    * **JSON Conversion:**  Transforms the refined slide deck text into a structured JSON format for easier processing.
* **Imagen for Visuals:**  Generates relevant and engaging images for each slide based on the AI-generated descriptions.
* **PDF Generation:** Compiles the slides, including titles, descriptions, key takeaways, and images, into a downloadable PDF presentation.
* **Gradio Interface:**  Provides a user-friendly interface for topic input, refinement level selection, and presentation download.

## Architecture

1. **User Input:** The user provides a presentation topic through the Gradio interface.
2. **Story Generation:** A Gemini generates a detailed story relevant to the topic.
3. **Slide Generation & Refinement:**  Another agents converts the story into a slide deck, which is then refined iteratively by a  refinement agent.
4. **JSON Conversion:** The refined slide deck is converted to JSON format.
5. **Image Description & Generation:** An agent creates image descriptions for each slide. Imagen then uses these descriptions to generate relevant images.


## Getting Started

1. **Set up**
   - Set the `PROJECT_ID` and `LOCATION` variables in the code.
2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Application:**
   ```bash
   gradio app.py 
   ```

