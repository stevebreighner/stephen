import os
import re
import html

BLOG_DIR = "src/content/blog"

for filename in os.listdir(BLOG_DIR):
    if not filename.endswith(".md"):
        continue

    path = os.path.join(BLOG_DIR, filename)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    parts = content.split("---", 2)

    if len(parts) != 3:
        continue

    frontmatter = parts[1]
    body = parts[2]

    # TikTok detection
    if "tiktok.com" in content.lower():
        description = "A TikTok video"
    else:
        text = re.sub("<[^>]+>", " ", body)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()

        description = text[:160]
        if len(text) > 160:
            description += "..."

    # Replace existing description or add one
    if re.search(r"^description:", frontmatter, re.MULTILINE):
        frontmatter = re.sub(
            r'^description:.*$',
            f'description: "{description.replace(chr(34), chr(92)+chr(34))}"',
            frontmatter,
            flags=re.MULTILINE
        )
    else:
        frontmatter = (
            frontmatter.rstrip()
            + f'\ndescription: "{description}"\n'
        )

    new_content = "---" + frontmatter + "---" + body

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Updated:", filename)
