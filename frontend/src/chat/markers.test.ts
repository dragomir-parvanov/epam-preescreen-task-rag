import { describe, expect, test } from "vite-plus/test";
import { splitMarkers, stripMarkers } from "./markers";

describe("stripMarkers", () => {
  test("removes markers with the space before them", () => {
    expect(stripMarkers("Use the header [3]. It is signed [1][4] with HMAC [2, 5].")).toBe(
      "Use the header. It is signed with HMAC.",
    );
  });

  test("hides a marker that is still arriving at the end of the stream", () => {
    expect(stripMarkers("Use the header [")).toBe("Use the header");
    expect(stripMarkers("Use the header [1")).toBe("Use the header");
    expect(stripMarkers("Use the header [1, ")).toBe("Use the header");
  });

  test("leaves bracketed text that isn't a marker", () => {
    expect(stripMarkers("Set the role to [read-only], see [doc2] and [1-3].")).toBe(
      "Set the role to [read-only], see [doc2] and [1-3].",
    );
  });
});

describe("splitMarkers", () => {
  test("splits text into runs and Citation numbers", () => {
    expect(splitMarkers("Signed [1][2], rotated yearly [1].")).toEqual([
      "Signed",
      { n: 1 },
      { n: 2 },
      ", rotated yearly",
      { n: 1 },
      ".",
    ]);
  });

  test("returns plain text unchanged", () => {
    expect(splitMarkers("No markers here.")).toEqual(["No markers here."]);
  });
});
