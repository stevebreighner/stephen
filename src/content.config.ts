import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const cards = defineCollection({
  loader: glob({
    pattern: "**/*.md",
    base: "./src/content/cards",
  }),
  schema: z.object({
    title: z.string(),
    image: z.string(),
    price: z.string().optional(),
  }),
});

export const collections = {
  cards,
};
