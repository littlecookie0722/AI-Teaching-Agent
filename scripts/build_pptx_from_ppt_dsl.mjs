#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

async function pathExists(value) {
  try {
    await fs.access(value);
    return true;
  } catch {
    return false;
  }
}

async function findFirstExisting(candidates) {
  for (const candidate of candidates) {
    if (await pathExists(candidate)) return candidate;
  }
  return undefined;
}

async function findPresentationsSkillDir() {
  if (process.env.PRESENTATIONS_SKILL_DIR) {
    return process.env.PRESENTATIONS_SKILL_DIR;
  }
  const presentationsRoot = path.join(
    os.homedir(),
    ".codex",
    "plugins",
    "cache",
    "openai-primary-runtime",
    "presentations",
  );
  if (!(await pathExists(presentationsRoot))) {
    throw new Error(`Presentations runtime not found: ${presentationsRoot}`);
  }
  const entries = await fs.readdir(presentationsRoot, { withFileTypes: true });
  const versions = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort((a, b) => b.localeCompare(a, undefined, { numeric: true }));
  for (const version of versions) {
    const skillDir = path.join(presentationsRoot, version, "skills", "presentations");
    const utilsPath = path.join(skillDir, "container_tools", "artifact_tool_utils.mjs");
    if (await pathExists(utilsPath)) return skillDir;
    const legacyUtilsPath = path.join(skillDir, "scripts", "artifact_tool_utils.mjs");
    if (await pathExists(legacyUtilsPath)) return skillDir;
  }
  throw new Error(`No presentations skill runtime with artifact_tool_utils.mjs under ${presentationsRoot}`);
}

const PRESENTATIONS_SKILL_DIR = await findPresentationsSkillDir();
const SKILL_UTILS = await findFirstExisting([
  path.join(PRESENTATIONS_SKILL_DIR, "container_tools", "artifact_tool_utils.mjs"),
  path.join(PRESENTATIONS_SKILL_DIR, "scripts", "artifact_tool_utils.mjs"),
]);
if (!SKILL_UTILS) {
  throw new Error(`artifact_tool_utils.mjs not found under ${PRESENTATIONS_SKILL_DIR}`);
}

const {
  createSlideContext,
  ensureArtifactToolWorkspace,
  importArtifactTool,
  parseArgs,
  saveBlobToFile,
} = await import(pathToFileURL(SKILL_UTILS).href);

function usage() {
  return [
    "Usage:",
    "  node scripts/build_pptx_from_ppt_dsl.mjs --dsl <ppt.json> --out <artifact.pptx> [--manifest <manifest.json>] [--preview <slide-01.png>] [--preview-dir <dir>] [--contact-sheet <sheet.png>] [--workspace <dir>]",
  ].join("\n");
}

function requireArg(args, key) {
  const value = args[key];
  if (!value) {
    throw new Error(`Missing required --${key}.\n${usage()}`);
  }
  return value;
}

function normalizeText(value, fallback = "") {
  return String(value ?? fallback).replace(/\s+/g, " ").trim();
}

function slideTypeLabel(type) {
  if (type === "title") return "TITLE";
  if (type === "summary") return "SUMMARY";
  return "CONTENT";
}

function deckPalette(style) {
  if (String(style || "").toLowerCase().includes("dark")) {
    return {
      background: "#111827",
      surface: "#1f2937",
      text: "#f9fafb",
      muted: "#cbd5e1",
      accent: "#2dd4bf",
      accentSoft: "#134e4a",
      line: "#334155",
    };
  }
  return {
    background: "#f7fafc",
    surface: "#ffffff",
    text: "#172033",
    muted: "#667085",
    accent: "#0f766e",
    accentSoft: "#e7f8f2",
    line: "#d9e0ea",
  };
}

function padSlideNumber(value) {
  return String(value).padStart(2, "0");
}

async function runContactSheet(previewPaths, outputPath) {
  if (!outputPath || previewPaths.length === 0) return undefined;
  const scriptPath = await findFirstExisting([
    path.join(PRESENTATIONS_SKILL_DIR, "template_following_scripts", "make_contact_sheet.py"),
    path.join(path.dirname(fileURLToPath(pathToFileURL(SKILL_UTILS).href)), "make_contact_sheet.py"),
  ]);
  if (!scriptPath) {
    await fs.copyFile(previewPaths[0], outputPath);
    return outputPath;
  }
  const python = process.env.PYTHON || "python";
  const result = spawnSync(
    python,
    [scriptPath, "--output", outputPath, ...previewPaths],
    { encoding: "utf8" },
  );
  if (result.status !== 0) {
    await fs.copyFile(previewPaths[0], outputPath);
    return outputPath;
  }
  return outputPath;
}

function addFooter(ctx, slide, ppt, slideIndex, slideTotal, palette) {
  ctx.addText(slide, {
    name: `footer-${slideIndex}`,
    text: `${ppt.metadata.id} · WAITING_REVIEW · ${slideIndex}/${slideTotal}`,
    left: 56,
    top: 664,
    width: 820,
    height: 24,
    fontSize: 11,
    color: palette.muted,
    typeface: ctx.fonts.body,
  });
  ctx.addText(slide, {
    name: `footer-policy-${slideIndex}`,
    text: "reviewRequired=true · autoPublishAllowed=false · realPublish=false",
    left: 884,
    top: 664,
    width: 340,
    height: 24,
    fontSize: 11,
    color: palette.muted,
    align: "right",
    typeface: ctx.fonts.body,
  });
}

function addBackground(ctx, slide, palette) {
  ctx.addShape(slide, {
    name: "slide-background",
    left: 0,
    top: 0,
    width: 1280,
    height: 720,
    fill: palette.background,
    line: ctx.line("#00000000", 0),
  });
}

function addTitleSlide(ctx, slide, ppt, dslSlide, palette, index, total) {
  addBackground(ctx, slide, palette);
  ctx.addText(slide, {
    name: "kicker-label",
    text: `${slideTypeLabel(dslSlide.type)} · ${ppt.spec.theme.language}`,
    left: 64,
    top: 74,
    width: 520,
    height: 26,
    fontSize: 13,
    bold: true,
    color: palette.accent,
    typeface: ctx.fonts.body,
  });
  ctx.addText(slide, {
    name: "title",
    text: normalizeText(dslSlide.title, ppt.metadata.title),
    left: 64,
    top: 156,
    width: 820,
    height: 128,
    fontSize: 48,
    bold: true,
    color: palette.text,
    typeface: ctx.fonts.title,
  });
  ctx.addText(slide, {
    name: "subtitle",
    text: normalizeText(dslSlide.subtitle, `${ppt.metadata.audience} · ${ppt.metadata.durationMinutes} min`),
    left: 66,
    top: 302,
    width: 760,
    height: 56,
    fontSize: 24,
    color: palette.muted,
    typeface: ctx.fonts.body,
  });
  ctx.addShape(slide, {
    name: "accent-rule",
    left: 66,
    top: 400,
    width: 360,
    height: 6,
    fill: palette.accent,
    line: ctx.line("#00000000", 0),
  });
  ctx.addText(slide, {
    name: "review-card",
    text: "AI generated PPT DSL artifact\nStatus: WAITING_REVIEW\nPPTX artifact: local PoC only",
    left: 850,
    top: 168,
    width: 330,
    height: 176,
    fontSize: 20,
    color: palette.text,
    fill: palette.surface,
    line: ctx.line(palette.line, 1),
    insets: { left: 22, right: 22, top: 18, bottom: 18 },
    typeface: ctx.fonts.body,
  });
  addFooter(ctx, slide, ppt, index, total, palette);
}

function addContentSlide(ctx, slide, ppt, dslSlide, palette, index, total) {
  addBackground(ctx, slide, palette);
  ctx.addText(slide, {
    name: "kicker-label",
    text: `${slideTypeLabel(dslSlide.type)} · SLIDE ${index}`,
    left: 56,
    top: 42,
    width: 360,
    height: 24,
    fontSize: 12,
    bold: true,
    color: palette.accent,
    typeface: ctx.fonts.body,
  });
  ctx.addText(slide, {
    name: "title",
    text: normalizeText(dslSlide.title, `Slide ${index}`),
    left: 56,
    top: 84,
    width: 940,
    height: 72,
    fontSize: 34,
    bold: true,
    color: palette.text,
    typeface: ctx.fonts.title,
  });

  const bullets = Array.isArray(dslSlide.bullets) && dslSlide.bullets.length > 0
    ? dslSlide.bullets
    : [normalizeText(dslSlide.subtitle, "请在审核后补充讲解内容。")];
  const startTop = 190;
  bullets.slice(0, 6).forEach((bullet, bulletIndex) => {
    const top = startTop + bulletIndex * 64;
    ctx.addShape(slide, {
      name: `bullet-marker-${bulletIndex + 1}`,
      left: 78,
      top: top + 10,
      width: 11,
      height: 11,
      fill: palette.accent,
      line: ctx.line("#00000000", 0),
    });
    ctx.addText(slide, {
      name: `bullet-text-${bulletIndex + 1}`,
      text: normalizeText(bullet),
      left: 106,
      top,
      width: 830,
      height: 46,
      fontSize: 23,
      color: palette.text,
      typeface: ctx.fonts.body,
    });
  });

  ctx.addText(slide, {
    name: "review-side-rail",
    text: "Review checklist\n- DSL schema validated\n- Manual approval required\n- Real publish disabled",
    left: 966,
    top: 184,
    width: 246,
    height: 210,
    fontSize: 18,
    color: palette.text,
    fill: palette.accentSoft,
    line: ctx.line("#00000000", 0),
    insets: { left: 18, right: 18, top: 18, bottom: 18 },
    typeface: ctx.fonts.body,
  });
  addFooter(ctx, slide, ppt, index, total, palette);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(usage());
    return;
  }

  const dslPath = path.resolve(requireArg(args, "dsl"));
  const outPath = path.resolve(requireArg(args, "out"));
  const manifestPath = args.manifest ? path.resolve(args.manifest) : undefined;
  const previewPath = args.preview ? path.resolve(args.preview) : undefined;
  const previewDir = args["preview-dir"] ? path.resolve(args["preview-dir"]) : undefined;
  const contactSheetPath = args["contact-sheet"] ? path.resolve(args["contact-sheet"]) : undefined;
  const workspace = path.resolve(args.workspace || path.join(path.dirname(outPath), ".pptx-artifact-workspace"));
  const raw = await fs.readFile(dslPath, "utf8");
  const ppt = JSON.parse(raw);
  const slides = ppt?.spec?.slides;
  if (!Array.isArray(slides) || slides.length === 0) {
    throw new Error("PPT DSL must include spec.slides.");
  }

  await ensureArtifactToolWorkspace(workspace);
  const artifact = await importArtifactTool(workspace);
  const { Presentation, PresentationFile } = artifact;
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
  const ctx = createSlideContext(artifact, {
    slideSize: { width: 1280, height: 720 },
    outputDir: path.dirname(outPath),
    workspaceDir: workspace,
  });
  const palette = deckPalette(ppt?.spec?.theme?.style);

  slides.forEach((dslSlide, index) => {
    const slide = presentation.slides.add();
    if (dslSlide.type === "title" || index === 0) {
      addTitleSlide(ctx, slide, ppt, dslSlide, palette, index + 1, slides.length);
    } else {
      addContentSlide(ctx, slide, ppt, dslSlide, palette, index + 1, slides.length);
    }
  });

  const pptx = await PresentationFile.exportPptx(presentation);
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await pptx.save(outPath);

  const stat = await fs.stat(outPath);
  const firstSlide = slides[0] || {};
  let previewImagePath = null;
  let previewBytes = 0;
  let previewRenderAttempted = false;
  let previewReason = "PREVIEW_OUTPUT_NOT_REQUESTED";
  const slidePreviews = [];
  const renderSlidePreview = async (slideIndex, targetPath) => {
    const previewBlob = await presentation.export({
      slide: presentation.slides.getItem(slideIndex),
      format: "png",
      scale: Number.parseFloat(args["preview-scale"] || "0.5"),
    });
    await saveBlobToFile(previewBlob, targetPath);
    const previewStat = await fs.stat(targetPath);
    if (previewStat.size <= 0) {
      throw new Error(`Preview image is empty: ${targetPath}`);
    }
    return previewStat.size;
  };

  if (previewPath || previewDir) {
    previewRenderAttempted = true;
    const basePreviewDir = previewDir || path.dirname(previewPath);
    await fs.mkdir(basePreviewDir, { recursive: true });
    for (let index = 0; index < slides.length; index += 1) {
      const targetPath = !previewDir && index === 0 && previewPath
        ? previewPath
        : path.join(basePreviewDir, `slide-${padSlideNumber(index + 1)}.png`);
      const bytes = await renderSlidePreview(index, targetPath);
      const dslSlide = slides[index] || {};
      slidePreviews.push({
        index: index + 1,
        id: dslSlide.id || null,
        title: normalizeText(dslSlide.title, `Slide ${index + 1}`),
        type: dslSlide.type || (index === 0 ? "title" : "content"),
        imagePath: targetPath,
        thumbnailPath: targetPath,
        bytes,
      });
    }
    if (previewPath && slidePreviews[0]?.imagePath && slidePreviews[0].imagePath !== previewPath) {
      await fs.mkdir(path.dirname(previewPath), { recursive: true });
      await fs.copyFile(slidePreviews[0].imagePath, previewPath);
      const previewStat = await fs.stat(previewPath);
      previewImagePath = previewPath;
      previewBytes = previewStat.size;
    } else {
      previewImagePath = slidePreviews[0]?.imagePath || null;
      previewBytes = slidePreviews[0]?.bytes || 0;
    }
    previewReason = "PREVIEW_RENDERED";
  }
  let contactSheet = undefined;
  if (contactSheetPath && slidePreviews.length > 0) {
    await fs.mkdir(path.dirname(contactSheetPath), { recursive: true });
    const sheetPath = await runContactSheet(slidePreviews.map((item) => item.imagePath), contactSheetPath);
    const sheetStat = await fs.stat(sheetPath);
    contactSheet = {
      path: sheetPath,
      bytes: sheetStat.size,
      slideCount: slidePreviews.length,
    };
  }
  const preview = {
    previewAvailable: Boolean(previewImagePath),
    renderAttempted: previewRenderAttempted,
    reason: previewReason,
    slidePreviews,
    contactSheet,
    firstSlide: {
      id: firstSlide.id || null,
      title: normalizeText(firstSlide.title, ppt?.metadata?.title || "Untitled"),
      type: firstSlide.type || "title",
      imagePath: previewImagePath,
      thumbnailPath: previewImagePath,
      bytes: previewBytes,
    },
  };
  const result = {
    mode: "LOCAL_PPTX_ARTIFACT_POC",
    dslPath,
    pptxPath: outPath,
    slideCount: slides.length,
    bytes: stat.size,
    generator: "@oai/artifact-tool/presentation-jsx",
    preview,
    safety: {
      realLlmCalled: false,
      newLlmRequestSent: false,
      secretsRead: false,
      networkAccess: false,
      realCloudResourceChanged: false,
      sandboxExecuted: false,
      contestantCodeExecuted: false,
      autoPublishAllowed: false,
      realPublish: false,
    },
  };
  if (manifestPath) {
    await fs.mkdir(path.dirname(manifestPath), { recursive: true });
    await fs.writeFile(manifestPath, `${JSON.stringify(result, null, 2)}\n`, "utf8");
  }
  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  console.error(usage());
  process.exit(1);
});
