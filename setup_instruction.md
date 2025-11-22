# Vidi-Q Setup Instructions

## Prerequisites

* **Python 3.8+**

  * Check your installed version by running:

    ```cmd
    python --version
    ```
  * If the version is lower than 3.8, install Python 3.8 or higher.

---

## Installation Steps

### Install Manim

1. Open **Command Prompt** and run:

   ```cmd
   pip install manim
   ```

### Install MikTeX

1. Download the installer from the [MikTeX official website](https://miktex.org/download).
2. Install MikTeX.
3. Open the **Start Menu**, search for **MikTeX Console**, and launch it.
4. In the console, click **Check for Updates**, then click **Update Now** to install all updates.

### Install FFmpeg

1. Download the latest Windows build from this [link](https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl-shared.zip).
2. Create a directory:
   `C:\ffmpeg`
3. Move the downloaded `.zip` file to:
   `C:\ffmpeg\ffmpeg-master-latest-win64-gpl-shared.zip`
4. Extract the `.zip` file inside `C:\ffmpeg`.
5. Open the **Start Menu** and search for **Edit the system environment variables**.
6. In the dialog, click **Environment Variables**.
7. Under **User variables**, select **Path**, click **Edit**, then click **New**, and add:

   ```
   C:\ffmpeg\ffmpeg-master-latest-win64-gpl\bin
   ```

---

## Clone the Repository

1. Clone the repository:

   ```cmd
   git clone https://github.com/Mukesh-charan/Vidi-Q.git
   ```
2. Navigate into the project directory:

   ```cmd
   cd Vidi-Q
   ```
3. Install the required dependencies:

   ```cmd
   pip install -r requirements.txt
   ```

---

### Manim Voiceover Setup

* Install the `manim-voiceover` package by following the [official documentation](https://voiceover.manim.community/en/stable/installation.html).

---

## API Configuration (Required)

To use Google Gemini, Zapier, and Supabase integrations, you must configure API credentials.

1. Create a `.env` file in the **root directory** of the project.
   Add the following environment variables:

   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ZAPIER_WEBHOOK_URL=your_zapier_webhook_url_here
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_ANON_KEY=your_supabase_anon_key_here
   ```

2. Update the **frontend (`index.html`)** with the same keys at the following lines:

   * Line 55 → `SUPABASE_URL`
   * Line 56 → `SUPABASE_ANON_KEY`
   * Line 191 → `GEMINI_API_KEY`

3. Update the **backend (`llm_handler.py`)**:

   * Line 7 → `GEMINI_API_KEY`

---

## Running the Code

1. Open **Command Prompt** in the project directory and run:

   ```cmd
   python server.py
   ```
2. Open `index.html` in your browser.
3. The web app is now ready to use!
