import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vite-plus/test";
import { Markdown } from "./Markdown";

test("renders paragraphs separated by blank lines", () => {
  const { container } = render(<Markdown text={"First paragraph.\n\nSecond paragraph."} />);

  const paragraphs = container.querySelectorAll("p");
  expect([...paragraphs].map((p) => p.textContent)).toEqual([
    "First paragraph.",
    "Second paragraph.",
  ]);
});

test("renders bulleted and numbered lists, even straight after a line of text", () => {
  render(<Markdown text={"Steps:\n1. Open Settings\n2. Click SSO\n\nNotes:\n- one\n* two"} />);

  const [ordered, bulleted] = screen.getAllByRole("list");
  expect(ordered?.tagName).toBe("OL");
  expect(
    within(ordered ?? document.body)
      .getAllByRole("listitem")
      .map((li) => li.textContent),
  ).toEqual(["Open Settings", "Click SSO"]);
  expect(bulleted?.tagName).toBe("UL");
  expect(
    within(bulleted ?? document.body)
      .getAllByRole("listitem")
      .map((li) => li.textContent),
  ).toEqual(["one", "two"]);
  expect(screen.getByText("Steps:")).toBeInTheDocument();
});

test("renders inline code, bold text and fenced code blocks", () => {
  const { container } = render(
    <Markdown
      text={"Send **both** headers: `X-Nimbus-Signature`.\n\n```http\nX-Nimbus-Signature: t=1\n```"}
    />,
  );

  expect(screen.getByText("X-Nimbus-Signature", { selector: "code" })).toBeInTheDocument();
  expect(screen.getByText("both", { selector: "strong" })).toBeInTheDocument();
  expect(container.querySelector("pre")?.textContent).toBe("X-Nimbus-Signature: t=1");
});

test("shows HTML in the text as text, never as markup", () => {
  const { container } = render(<Markdown text={'Use <img src=x onerror="alert(1)"> here.'} />);

  expect(container.querySelector("img")).toBeNull();
  expect(screen.getByText('Use <img src=x onerror="alert(1)"> here.')).toBeInTheDocument();
});

test("hands Citation markers to renderMarker, inside lists too", () => {
  render(
    <Markdown
      text={"Signed with HMAC [1].\n\n- Rotated yearly [2]"}
      renderMarker={(n) => <sup data-testid="marker">{n}</sup>}
    />,
  );

  expect(screen.getAllByTestId("marker").map((m) => m.textContent)).toEqual(["1", "2"]);
});

test("leaves markers as written when there's no renderMarker", () => {
  render(<Markdown text="Signed with HMAC [1]." />);

  expect(screen.getByText("Signed with HMAC [1].")).toBeInTheDocument();
});
