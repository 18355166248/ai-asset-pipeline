import { readFile, mkdir, writeFile, cp, rm } from "node:fs/promises";
import { createHash } from "node:crypto";
import { pathToFileURL, fileURLToPath } from "node:url";
import { resolve } from "node:path";
const sourceFile = new URL("../.local-source.json", import.meta.url);
let saved;
try {
  saved = JSON.parse(await readFile(sourceFile, "utf8")).run;
} catch {
  /* 首次启动使用默认试点。 */
}
const arg = process.argv.indexOf("--run");
const run =
  arg >= 0
    ? pathToFileURL(resolve(process.argv[arg + 1]) + "/")
    : saved
      ? pathToFileURL(saved + "/")
      : new URL("../../output/sprite-gen-pilot-v1/", import.meta.url);
const target = new URL("../public/data/pilot/", import.meta.url);
// 只发布当前试点冻结帧，不把整个output、原图候选或引擎缓存暴露给前端。
let contract, proof;
try {
  contract = await readFile(new URL("motion-contract.json", run));
  proof = JSON.parse(
    await readFile(new URL("compose-proof.json", run), "utf8"),
  );
} catch (error) {
  // 新检出没有ignored试点产物时仍可使用流水线；显式指定错误批次则报错，不沿用旧图。
  if (error.code === "ENOENT" && arg < 0) {
    await rm(target, { recursive: true, force: true });
    console.warn(
      "尚未准备动作素材，可先使用/pipeline；导入后用prepare:data --run指定真实批次。",
    );
    process.exit(0);
  }
  throw error;
}
// 读取源文件成功后才清理派生缓存，切批次时不遗留旧角色的冻结帧。
await rm(target, { recursive: true, force: true });
await mkdir(target, { recursive: true });
await cp(new URL("frozen/", run), new URL("frozen/", target), {
  recursive: true,
});
await writeFile(
  new URL("review-data.json", target),
  JSON.stringify({
    contract: JSON.parse(contract),
    proof,
    baselineSha256: createHash("sha256").update(contract).digest("hex"),
    run: fileURLToPath(run).replace(/\/$/, ""),
  }),
);

await writeFile(
  sourceFile,
  JSON.stringify({ run: fileURLToPath(run).replace(/\/$/, "") }),
);
