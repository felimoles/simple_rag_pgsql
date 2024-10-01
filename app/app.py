import streamlit as st
from pathlib import Path #to get absolute path
from langchain.agents import create_sql_agent 
from langchain import SQLDatabase
from langchain.agents.agent_types import AgentType
from langchain.callbacks import StreamlitCallbackHandler
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from sqlalchemy import create_engine
import sqlite3
from langchain_openai import ChatOpenAI
import os
from dotenv import dotenv_values

config = dotenv_values(".env")

st.title("SQLRAG : Chat With PGSQL")
st.baseUrl = "https://localhost:8501"
LOCALDB = "USE_LOCAL" 
PGSQL = "USE_PGSQL"

radio_opt = ["Use Sqlite3 database Employee.db","Connect to your PGSQL Database"]

selected_opt = st.sidebar.radio(label="Choose Database to connect and chat",options=radio_opt)

pgsql_user = config["POSTGRES_USER"]
pgsql_password = config["POSTGRES_PASSWORD"]
pgsql_host = config["POSTGRES_HOST"]
pgsql_db = config["POSTGRES_DB"]

#TO SUPORT DATA FROM FORM
if radio_opt.index(selected_opt)==1:
    db_uri=PGSQL
    #mysql_host = st.sidebar.text_input("Provide MYSQL Host")
    #mysql_user = st.sidebar.text_input("My Sql User")
    #mysql_password = st.sidebar.text_input("Provide MYSQL Pass",type="password")
    #mysql_db = st.sidebar.text_input("MySQL Database")

else:
    db_uri=LOCALDB

if not db_uri:
    st.info("Please enter database info and uri")

 

#llm = ChatGroq(groq_api_key=api_key,model_name="gemma2-9b-it",streaming=True)
llm = ChatOpenAI(
        model=config["OPENAI_MODEL"],
        temperature=0.2,
        max_retries=2,
        api_key=config["OPENAI_API_KEY"],
    )


def configure(db_uri,mysql_host=None,mysql_user=None,mysql_password=None,mysql_db=None):
    if db_uri==LOCALDB:
        dbfilepath = (Path(__file__).parent/"employee.db").absolute()
        print(dbfilepath)
        creator = lambda: sqlite3.connect(f"file:{dbfilepath}?mode=ro",uri=True)
        return SQLDatabase(create_engine("sqlite:///",creator=creator))
    
    elif db_uri==PGSQL:
        if not (mysql_host and mysql_user and mysql_password and mysql_db):
            st.error("Please provide all MYSQL connection details")
            st.stop()
        return SQLDatabase(create_engine("postgresql+psycopg2://"+pgsql_user+":"+pgsql_password+"@"+pgsql_host+"/"+pgsql_db+""))
    
        

if db_uri==PGSQL:
    db=configure(db_uri,pgsql_user,pgsql_password,pgsql_host,pgsql_db)
else:
    db=configure(db_uri)


#Configure the SQLtoolkit
toolkit = SQLDatabaseToolkit(db=db,llm=llm)

agent = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)


#create session state to maintain chat history

if "messages" not in st.session_state or st.sidebar.button("Clear Message History"):
    st.session_state["messages"]=[{"role":"assistant","content":"Como puedo ayudarte?"}]


#loop thorough each message

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


user_query = st.chat_input(placeholder="Preguntame algo sobre la base de datos")

if user_query:
    st.session_state.messages.append({"role":"user","content":user_query})
    st.chat_message("user").write(user_query)


    with st.chat_message("assistant"):
        st_cb = StreamlitCallbackHandler(st.container())
        response = agent.run(user_query,callbacks=[st_cb])
        st.session_state.messages.append({"role":"assistant","content":response})
        st.write(response)