"""Auto-generate Streamlit UI pages from toolkit modules."""
import inspect
import importlib
from pathlib import Path


def generate_streamlit_ui(module_name: str, output_path: str):
    module = importlib.import_module(module_name)
    functions = inspect.getmembers(module, inspect.isfunction)

    with open(output_path, "w") as f:
        f.write("import streamlit as st\n")
        f.write(f"import {module_name}\n\n")
        f.write(f"st.title('Auto-generated UI for {module_name}')\n\n")

        for name, func in functions:
            sig = inspect.signature(func)
            f.write(f"st.header('{name}')\n")
            for param in sig.parameters.values():
                default = param.default if param.default != inspect._empty else ""
                f.write(f"{param.name} = st.text_input('{param.name}', '{default}')\n")
            f.write(f"if st.button('Run {name}'):\n")
            args = ", ".join(sig.parameters.keys())
            f.write(f"    st.write({module_name}.{name}({args}))\n\n")


def main():
    modules = [
        "socrata_toolkit.client",
        "socrata_toolkit.analysis",
        "socrata_toolkit.spatial"
    ]
    Path("streamlit_app").mkdir(exist_ok=True)
    for m in modules:
        output = f"streamlit_app/auto_{m.split('.')[-1]}_ui.py"
        generate_streamlit_ui(m, output)
        print(f"Generated {output}")


if __name__ == "__main__":
    main()
