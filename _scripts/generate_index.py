"""Generate the index page using the README.md file and fixing the cross links."""

import re
from pathlib import Path

import mkdocs_gen_files

root = Path(__file__).parents[2]
readme_file = root / "README.md"


def replace_links(readme_content: str) -> str:
    """Replace the relative links to the overview page by removing the .md extension."""
    readme_content = readme_content.replace("docs/", "")
    # replace the relative links to the overview page by removing the .md extension
    return re.sub(r"/\w+\.md", lambda match: match.group(0)[:-3], readme_content)


LOGO_LINES = (
    "![Mapyta logo](assets/images/mapyta-logo-light-mode.svg#only-light){ display: flex; justify-content: center; align-items: center; }\n"
    "![Mapyta logo](assets/images/mapyta-logo-dark-mode.svg#only-dark){ display: flex; justify-content: center; align-items: center; }\n"
)

with open(readme_file, encoding="utf-8") as fd:
    readme_content = fd.read()
    readme_content = replace_links(readme_content)
    # Replace lines 1-5 (the HTML logo block) with MkDocs-style image tags
    lines = readme_content.splitlines(keepends=True)
    readme_content = LOGO_LINES + "".join(lines[5:])

with mkdocs_gen_files.open("index.md", "w") as fd:
    # hide navigation in the index page
    fd.writelines(["---\n", "hide:\n", "  - navigation\n", "---\n"])
    fd.write(readme_content)

    # hide the first h1 tag
    fd.write("\n<style>\n")
    fd.write("  h1:first-of-type {\n")
    fd.write("    display: none;\n")
    fd.write("  }\n")
    fd.write("</style>\n")
