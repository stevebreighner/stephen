import { defineCollection } from "astro:content";
import { z } from "astro/zod";

const blog = defineCollection({
  schema: z.object({
    title: z.string(),
    date: z.string(),
  }),
});

const artwork = defineCollection({
  schema: z.object({
    title: z.string(),
    medium: z.string(),
    date: z.string(),
    image: z.string(),
    thumb: z.string().optional(),
    thumbs: z
      .object({
        portrait: z.string().optional(),
        landscape: z.string().optional(),
        square: z.string().optional(),
      })
      .optional(),
    orientation: z.string().optional(),
    size: z.string().optional(),
    price: z.string().optional(),
    status: z.string().optional(),
  }),
});

export const collections = {
  blog,
  artwork,
};