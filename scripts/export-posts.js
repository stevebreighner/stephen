import mysql from "mysql2/promise";
import fs from "fs-extra";

const db = await mysql.createConnection({
  host: "localhost",
  user: "root",
  password: "yourpassword",
  database: "blog"
});

const [posts] = await db.query("SELECT * FROM posts");

await fs.ensureDir("./src/content/blog");

for (const post of posts) {
  const md = `---
title: "${post.title}"
date: "${post.created_at}"
slug: "${post.slug}"
---

${post.content}
`;

  await fs.writeFile(
    `./src/content/blog/${post.slug}.md`,
    md
  );
}

console.log("Export complete");
