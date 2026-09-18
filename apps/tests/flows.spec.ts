import {test,expect} from "@playwright/test";
test("citizen report and planner review through the running applications",async({browser})=>{
 const citizen=await browser.newPage();
 await citizen.goto("http://localhost:3000");
 await expect(citizen.getByRole("navigation")).toHaveCount(0);
 await citizen.getByLabel("Email",{exact:true}).fill("citizen@demo.local");
 await citizen.getByLabel("Password",{exact:true}).fill("CityDemo-2026!");
 await citizen.getByRole("button",{name:"Enter workspace"}).click();
 await expect(citizen.getByRole("heading",{name:"What’s happening nearby?"})).toBeVisible();
 await expect(citizen.getByText("DEMONSTRATION DATA",{exact:true})).toBeVisible();
 const description="Browser acceptance test: blocked drain "+Date.now();
 await citizen.getByLabel("Describe the issue").fill(description);
 await citizen.getByRole("button",{name:"Submit report"}).click();
 await expect(citizen.getByRole("status")).toContainText("Tracking ID");
 await expect(citizen.locator(".report").filter({hasText:description})).toBeVisible();
 await citizen.screenshot({path:"test-results/citizen.png",fullPage:true});
 const planner=await browser.newPage();
 await planner.goto("http://localhost:3001");
 await planner.getByLabel("Email",{exact:true}).fill("planner@demo.local");
 await planner.getByLabel("Password",{exact:true}).fill("CityDemo-2026!");
 await planner.getByRole("button",{name:"Enter workspace"}).click();
 await expect(planner.getByRole("heading",{name:"Indicators to review"})).toBeVisible();
 await planner.getByRole("button",{name:"Review eligible options"}).click();
 await expect(planner.locator(".plan")).toContainText("offline");
 await expect(planner.locator(".candidate").first()).toBeVisible();
 const report=planner.locator(".report").filter({hasText:description});
 await report.getByRole("button",{name:"Move to acknowledged"}).click();
 await expect(report).toContainText("acknowledged");
 await planner.screenshot({path:"test-results/planner.png",fullPage:true});
 await planner.getByRole("combobox",{name:"Study area"}).selectOption("2");
 await expect(planner.getByRole("button",{name:"Review eligible options"})).toBeDisabled();
 await citizen.close();await planner.close();
});

for (const role of ["citizen", "planner"]) {
 test(role + " login gates top navigation on desktop and mobile", async ({page}) => {
  await page.goto("http://localhost:" + (role === "citizen" ? "3000" : "3001"));
  await expect(page.getByRole("navigation")).toHaveCount(0);
  await expect(page.locator("#workspace")).toHaveCount(0);
  await expect(page.getByLabel("Email", {exact:true})).toHaveValue("");
  await expect(page.getByLabel("Password", {exact:true})).toHaveValue("");
  await page.getByLabel("Email", {exact:true}).fill(role + "@demo.local");
  await page.getByLabel("Password", {exact:true}).fill("CityDemo-2026!");
  await page.getByRole("button", {name:"Enter workspace"}).click();
  const nav = page.getByRole("navigation", {name:"Workspace navigation"});
  await expect(nav).toBeVisible();
  await expect(page.locator("aside")).toHaveCount(0);
  await expect(nav.getByRole("link", {name:role === "citizen" ? "My reports" : "Ward reports", exact:true})).toBeVisible();
  const navigationBox = await nav.boundingBox();
  const workspaceBox = await page.locator("#workspace").boundingBox();
  expect(navigationBox!.y + navigationBox!.height).toBeLessThanOrEqual(workspaceBox!.y);
  await page.setViewportSize({width:390,height:844});
  await expect(nav).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({path:"test-results/" + role + "-top-navigation-mobile.png"});
  await page.getByRole("button", {name:"Sign out",exact:true}).click();
  await expect(page.getByRole("navigation")).toHaveCount(0);
  await expect(page.locator("#workspace")).toHaveCount(0);
  await expect(page.getByLabel("Password", {exact:true})).toHaveValue("");
  await page.screenshot({path:"test-results/" + role + "-login-mobile.png"});
 });
}

test("SUMO traffic dots use recorded positions and support playback", async ({page}) => {
 let result:any;
 page.on("response", async response => {
  if (response.url().includes("/api/jobs/") && response.ok()) {
   const job=await response.json();
   if (job.status === "completed") result=job.result;
  }
 });
 await page.goto("http://localhost:3001");
 await expect(page.locator(".traffic-map")).toHaveCount(0);
 await page.getByLabel("Email",{exact:true}).fill("planner@demo.local");
 await page.getByLabel("Password",{exact:true}).fill("CityDemo-2026!");
 await page.getByRole("button",{name:"Enter workspace"}).click();
 await expect(page.locator(".traffic-map")).toHaveCount(2);
 await expect(page.locator(".traffic-map circle")).toHaveCount(0);
 await page.getByRole("button",{name:"Run comparison"}).click();
 const baseline=page.locator(".traffic-map").first();
 await expect(baseline.locator("circle").first()).toBeVisible({timeout:60000});
 await expect.poll(()=>result?.engine).toBe("SUMO/TraCI");
 const slider=page.getByRole("slider",{name:"Simulation time"});
 await expect(slider).toHaveValue("5");
 const frame=result.baseline.frames[5];
 await expect(baseline.locator("circle")).toHaveCount(frame.vehicles.length);
 await expect(baseline.locator("circle").first()).toHaveAttribute("cx",String(frame.vehicles[0].position[0]));
 await expect(baseline.locator("circle").first()).toHaveAttribute("cy",String(600-frame.vehicles[0].position[1]));
 const stopped=frame.vehicles.filter((v:any)=>v.speed_mps<0.1).length;
 await expect(baseline.locator('circle[fill="#d34343"]')).toHaveCount(stopped);
 await slider.focus();await slider.press("End");
 await expect(slider).toHaveValue(String(result.baseline.frames.length-1));
 await page.getByRole("button",{name:"Play traffic",exact:true}).click();
 await expect(slider).not.toHaveValue(String(result.baseline.frames.length-1));
 await page.getByRole("button",{name:"Pause playback",exact:true}).click();
 await page.locator("#simulation").screenshot({path:"test-results/traffic-dots.png"});
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
});
