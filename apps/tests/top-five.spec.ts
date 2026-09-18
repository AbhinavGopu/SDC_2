import {test,expect} from "@playwright/test";

test("planner displays five pending reports and promotes the next when resolved",async({page})=>{
 const reports=Array.from({length:7},(_,i)=>({id:"queue-fixture-"+i,ward_id:1,description:"Queue fixture issue "+i,status:i===0?"in_progress":"received",category:"traffic",created_at:"2026-01-01",authority:"Test fixture",analysis:{},media:[],priority:{level:i<2?"critical":"high",reason:"Test fixture",review:"Review promptly"}}));
 // Mock only report data; leave real login and the rest of the running UI intact.
 await page.route("**/api/complaints",route=>route.fulfill({json:reports}));
 await page.route("**/api/complaints/queue-fixture-0",async route=>{
  expect(route.request().postDataJSON().status).toBe("resolved");
  reports[0].status="resolved";
  await route.fulfill({json:reports[0]});
 });
 await page.goto("http://localhost:3001");
 await page.getByLabel("Email",{exact:true}).fill("planner@demo.local");
 await page.getByLabel("Password",{exact:true}).fill("CityDemo-2026!");
 await page.getByRole("button",{name:"Enter workspace"}).click();
 await expect(page.locator(".report")).toHaveCount(5);
 await expect(page.locator(".report").first()).toContainText("queue-fixture-0");
 await expect(page.locator(".report").last()).toContainText("queue-fixture-4");
 await page.locator(".report").first().getByRole("button",{name:"Move to resolved"}).click();
 await expect(page.locator(".report")).toHaveCount(5);
 await expect(page.locator(".report").first()).toContainText("queue-fixture-1");
 await expect(page.locator(".report").last()).toContainText("queue-fixture-5");
 await expect(page.locator(".report").filter({hasText:"queue-fixture-0"})).toHaveCount(0);
});
