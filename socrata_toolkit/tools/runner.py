import streamlit.web.cli as stcli
import os, sys

def resolve_path(path):
    resolved_path = os.path.abspath(os.path.join(os.getcwd(), path))
    return resolved_path

if __name__ == "__main__":
    # Points to the app.py file within the toolkit
    sys.argv = [
        "streamlit",
        "run",
        resolve_path("socrata_toolkit/app.py"),
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())
