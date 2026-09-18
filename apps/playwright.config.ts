import { defineConfig } from "@playwright/test";
export default defineConfig({ testDir:"./tests", timeout:60000, use:{headless:true}, reporter:[["list"],["html",{open:"never"}]], outputDir:"test-results" });
