# CareConnect: AI-Powered Healthcare Data Processing

## 🏥 Inspiration
Access to quality healthcare is a global challenge, with half the population lacking essential health services. Overcrowded systems, delayed diagnoses, and poor-quality care result in millions of preventable deaths annually. **CareConnect** was inspired by the need to bridge this gap by bringing healthcare closer to patients and supporting doctors in making faster, more accurate decisions.

## 🔍 What It Does
CareConnect processes medical data by storing it in a **Snowflake database**, where documents are divided into manageable chunks using **LangChain**. A hybrid search system powered by **Cortex Search** enables low-latency, high-quality retrieval of relevant information by combining **vector and keyword-based search**, ensuring precise and contextualized responses.

Users interact through a **Streamlit** interface to upload prescriptions or ask health-related questions, with relevant data extracted and matched from the database. This information is then processed by the **Mistral AI model** to generate accurate, context-aware responses, streamlining diagnosis and decision-making in healthcare.



https://github.com/user-attachments/assets/b0a5eb18-447d-41ae-99b7-5f74348c4341




## 🛠 How We Built It
- **Frontend**: Built with **Streamlit** for a user-friendly interface.
- **Backend**: Developed in **Python**, integrating with **Snowflake** for data storage and **Cortex Search** for processing.
- **Core Components**: Utilized **LangChain** for document processing, **Snowflake Cortex Search** for hybrid search, and **Mistral AI** for generating context-aware responses.

## 🚧 Challenges We Ran Into
- Processing large documents efficiently.
- Optimizing similarity searches for faster response times.
- Managing version issues during deployment.

## 🎉 Accomplishments That We're Proud Of
- Successfully implemented a **hybrid search system** with **Cortex Search** for more accurate results.
- Addressed and resolved technical challenges through thorough research, making the app highly **reliable and efficient**.

## 📚 What We Learned
- The importance of combining **vector-based and keyword-based search** using **Snowflake Cortex Search** for more accurate and contextually relevant results.
- Technical skills in **data management with Snowflake**, **hybrid search optimization using Cortex Search**, **AI integration**, and **full-stack development with Python and Streamlit**.

## 🚀 What's Next for CareConnect
✅ **Multilingual Support**: To make the system accessible globally.
✅ **Voice Inputs**: To enhance user interaction and accessibility.
✅ **Data Storage Expansion**: To include more comprehensive medical knowledge, improving the system’s overall effectiveness.

## 🏗 Built With
- **Cortex Search**
- **LLM**
- **Mistral AI**
- **Python**
- **RAG (Retrieval-Augmented Generation)**
- **Snowflake**
- **Streamlit**

## 🛠 Installation & Usage

### Run Locally

1. Clone this repository:
   ```bash
   git clone https://github.com/your-repo/careconnect.git
   ```

2. Navigate to the backend directory:
   ```bash
   cd careconnect/backend
   ```

3. Create a `.env` file in the backend directory and add the following environment variables:
   ```
   #SNOWFLAKE_USER=ITXXXX
   #SNOWFLAKE_PASSWORD=XXXXXX
   #SNOWFLAKE_ACCOUNT=XXXXXX
   
   aws_accesskey = XXXXXXXXXXXXX
   secret_key = XXXXXXXXXXXXXXXXXXXXXX
   ```

4. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```

---

### 📌 CareConnect: Transforming healthcare with AI-powered data processing for faster, more accurate medical insights.
