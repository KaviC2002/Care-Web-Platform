
# CARE Web Application

This project is a web-based platform for image detection and identification using pre-trained models. The platform supports conservationists in New Zealand by helping track and manage predator data using AI.

---

## Project Overview

- **Project Name:** CARE Web Platform
- **Project Management Tool:** [Photo of Gantt Chart](https://drive.google.com/file/d/1WZ3R1Ayi7kCne_SM6bAtEh4sfmM0queP/view?usp=sharing)
- **Description:** The CARE Web Application is designed for conservation purposes, enabling users to upload images, which are then analysed using pre-trained machine learning models. These models detect and identify various animal species, helping conservationists track and manage wildlife in New Zealand.
 - **Report:** [Go to Report](https://docs.google.com/document/d/1pgLAF_mdwlh7pg1WYHQuwZNGJDUVro-U/edit?usp=sharing&ouid=106380101047960053585&rtpof=true&sd=true)

---
## Technologies Used

- **Languages:** Python (3.12.X) 
- **Framework:** PyQT
- **Machine Learning Libraries:** 
  - PyTorch (1.9.0)
  - Torchvision (0.10.0)
- **Other Libraries:**
  - boto3 (1.18.46) for AWS S3 integration
  - SQLAlchemy for database management
  - python-dotenv for environment variable management
- **Database:** SQLite for local storage and AWS for cloud storage
- **Other Tools:** Docker (for deployment)
- Full List is available on requirements.txt

---

## Project Setup

There are three ways to set up the project depending on your preference. Choose one of the methods below.

---

### Method 1: Manual Setup (Recommended for Developers)

**Note: We recommend you have Python 3.12.X downloaded on your machine. This can be found [here](https://www.python.org/downloads/release/python-3125/).

#### 1. **Model Files**

You will need to place the required machine learning model files in the correct directories:

- **best_50.pt** – This file should be placed in the `app/detection_model/` directory. Make sure it is in the same directory as `best_50.txt`.
  [Download from Google Drive](https://drive.google.com/drive/folders/1J2YumOzkvFJM4_zIffPGeud7UIZu89_k?usp=drive_link)  

- **CARE_Traced.pt** – This file should also be placed in the `app/detection_model/` directory, where `Care_Traced.txt` is located.
  [Download from Google Drive](https://drive.google.com/file/d/1W0_vfDm1GxbRwrrn7AWOQDc_K-gNpiUA/view?usp=drive_link)

Make sure these files are correctly positioned as they are necessary for the detection functionality.

#### 2. **Environment Variables**

Create a `.env` file in the root directory of the project to store sensitive information like secret keys. You can get the required keys from the link here:
[Download from Google Drive](https://docs.google.com/document/d/1HD0-uQP0Z-VOKIvDft9pg6dEMeabiP_mV-digWatLpc/edit?usp=sharing)

Copy and Paste this into the .env file

Make sure the `.env` file is properly configured before running the application.

**OR**

If the above step is not working then you may replace line 35 and 36 in the app/app_pages/OnlineDatabasePage.py with the code below, insert the values from the link above into the variables below.

```python
access_key_id = ''
access_secret_key = ''
```


#### 3. **Set Up the Virtual Environment**

To ensure that all required dependencies are isolated within a virtual environment, follow these steps:

##### a. Mac Setup

```bash
python -m venv .venv
source .venv/bin/activate 

##### Install the Required Dependencies:
For Mac/Linux users, install all necessary Python packages specified in the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

#### For convenience, Mac users can also run the provided startup script, which activates the virtual environment and starts the app automatically. Run the script using the following command:

```bash
./startup.sh
```
Or right click on the startup script and click open.


##### b. Windows Setup:
For Windows users, the steps differ slightly.

1. Create the virtual environment:

```bash
python -m venv .venv
```

2. Activate the virtual environment:

```bash
.venv\Scripts\activate 
```

3. Install the Windows-specific dependencies from `windows_requirements.txt`:

```bash
pip install -r windows_requirements.txt
```


#### 4. **Run the Application**

Once the virtual environment is set up, run the application by executing the following command:

```bash
python main.py
```

For Windows users, run:

```bash
py main.py
```
---

### Method 2: Pre-Packaged Setup for Mac Users

For Mac users who prefer a simplified setup, you can download the pre-packaged application.
This package contains the application and all dependencies, so you can skip the manual setup steps.

[Download from Google Drive](https://drive.google.com/file/d/1_2GG71TKmSqwaHf0sZF8pulxs2IDQB3H/view?usp=share_link)

[![Watch a Video Guide](https://img.youtube.com/vi/wc8eeDBV16A/0.jpg)](https://youtu.be/wc8eeDBV16A)

📍 Watch the Demo Video: Click on the image above to view our demo on YouTube

**Note: This has not been optimised for MacOS 10 and earlier**

---

### Method 3: Pre-Zipped Setup for Windows Users

**Note: We recommend you have Python 3.12.X downloaded on your machine. This can be found [here](https://www.python.org/downloads/release/python-3125/).

If you prefer a pre-configured setup for Windows, you can download the zipped versions that include everything:
From here run the Windows Script:

[Download from Google Drive](https://drive.google.com/file/d/1iOSX895OhuvrFUyxgmKt8sTt-DxudTfj/view?usp=share_link)

[![Watch a Video Guide](https://img.youtube.com/vi/gvagVfmeUOo/0.jpg)](https://youtu.be/gvagVfmeUOo)

📍 Watch the Demo Video: Click on the image above to view our demo on YouTube 

---

### Method 4: Pre-Packaged Setup for Windows Users

If you prefer a packaged setup for Windows, you can download the packaged version that includes:

[Download from Google Drive](https://drive.google.com/file/d/1ybMlvFd2rittw1PpCeXaOhNUO_PfLYsS/view?usp=share_link)

[![Watch a Video Guide](https://img.youtube.com/vi/gtnOvkGWMuM/0.jpg)](https://youtu.be/gtnOvkGWMuM)

📍 Watch the Demo Video: Click on the image above to view our demo on YouTube

**Note: This version's processing is MUCH slower than Method 1,2,3. Due to time constraints, we could not optimise processing speed for the Windows packaged version. We recommend the other methods and to only use this method if you want to do no setup yourself. This is here as a proof of concept.**

**We also recommend leaving the online database toggled off as the online database has errors for this packaged application.**

---

## Application Credentials

For admin authorised access, use the following credentials:

- **Username**: `careweb@gmail.com`
- **Password**: `care24`

---

## Usage Examples

Once the application is running, users can upload images for detection. The app will provide confidence scores and identify the species in the image. Along with being able to run Reidentification on these images along with uploading this to a cloud database if the user decides to do so.

---

## Future Plans

- **Expansion of the AI Models:** Plan to incorporate upgraded/new AI models made by PHD students.
- **Enhanced UI:** Further UI improvements for a smoother user experience. Our app also is not responsive and is meant to be used in the min screen as is when it first opens up. When maximising the screen the layout becomes off centre, this is something to work on in future.
- **Cloud Deployment:** Aiming to optimise the cloud database so it does not cost as much as it does currently.
- **AWS Online Database** We spoke to our tutor Matthew about the AWS functionalities and it was explained this was a proof of concept. We would love to take this further in future iterations.

---

## Acknowledgements

Special thanks to:

- **Dr. Yun Sing** – For providing invaluable guidance and feedback as our client throughout the project.
- **Di and Justin** – PhD students who offered their insights and support in refining the project goals and objectives.
- **Matthew** – Our tutor, whose advice and feedback helped us stay on track and overcome challenges.
- **Anna** – Our lecturer, for her continuous support and leadership in guiding us through the course.
- **Team 13**: Sagar Patel, Senu Senathirajah, Kavi Chand, Martin Young, Maxwell Wrightson, Samuel Dong – for their hard work, collaboration, and dedication to delivering a successful project.

### Notes:
- The virtual environment is essential to isolate your project's dependencies. Always activate the environment before running the app.
- Windows users should ensure they install dependencies from `windows_requirements.txt`.
- If you encounter any issues with missing dependencies or models, ensure that all required files are correctly positioned and the `.env` file is properly configured.
- If you still are having problems with setting this up, do not hesitate to reach out to us. 

---
# Care-Web-Platform
