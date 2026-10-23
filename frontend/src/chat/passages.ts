import type { components } from "../api/schema";

type Passage = components["schemas"]["Passage"];

/**
 * Called with a Passage to show its whole Article, scrolled to its Section (`section.id`).
 * This is the seam Citation click-through (the Article panel) plugs into.
 */
export type OpenSection = (passage: Passage) => void;

/** "Article title › Section › Subsection". The Section path may repeat the title; it's shown once. */
export function passageLocation(passage: Passage): string {
  const { title } = passage.article;
  const path =
    passage.section.path[0] === title ? passage.section.path.slice(1) : passage.section.path;
  return [title, ...path].join(" › ");
}
