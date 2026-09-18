import {test,expect} from "@playwright/test";

test("advisor uses the priority queue with an empty placeholder-only brief",async({page,request})=>{
 const login=await request.post("http://localhost:8000/auth/login",{data:{email:"planner@demo.local",password:"CityDemo-2026!"}});
 const token=(await login.json()).token;
 const queue=await request.get("http://localhost:8000/complaints",{headers:{Authorization:"Bearer "+token}});
 const target=(await queue.json()).find((c:any)=>c.status!=="resolved");
 expect(target).toBeTruthy();
 await page.goto("http://localhost:3001");
 await page.getByLabel("Email",{exact:true}).fill("planner@demo.local");
 await page.getByLabel("Password",{exact:true}).fill("CityDemo-2026!");
 await page.getByRole("button",{name:"Enter workspace"}).click();
 const brief=page.getByLabel("Planning brief",{exact:true});
 await expect(brief).toHaveValue("");
 await expect(brief).toHaveAttribute("placeholder",/highest-priority complaint/);
 await expect(page.locator(".advisor-target")).toContainText(target.id);
 const response=page.waitForResponse(r=>r.url().endsWith("/api/plans") && r.request().method()==="POST");
 await page.getByRole("button",{name:"Review eligible options"}).click();
 const planResponse=await response;
 expect(planResponse.status()).toBe(201);
 expect(planResponse.request().postDataJSON().prompt).toBe("");
 expect((await planResponse.json()).result.target_complaint.id).toBe(target.id);
 await expect(page.locator(".plan")).toContainText(target.id);
 await expect(brief).toHaveValue("");
});

test("assigned reports display explained priorities in urgency order",async({page,request})=>{
 const login=await request.post("http://localhost:8000/auth/login",{data:{email:"citizen@demo.local",password:"CityDemo-2026!"}});
 const token=(await login.json()).token;
 const ids:string[]=[];
 for(const description of ["Festival procession next month needs route planning", "Festival procession tomorrow is blocking traffic", "Accident causing congestion at the main junction"]){
  const response=await request.post("http://localhost:8000/complaints",{headers:{Authorization:"Bearer "+token},data:{description:"Priority browser test: "+description,latitude:17.435,longitude:78.445}});
  expect(response.status()).toBe(201);ids.push((await response.json()).id);
 }
 await page.goto("http://localhost:3001");
 await page.getByLabel("Email",{exact:true}).fill("planner@demo.local");
 await page.getByLabel("Password",{exact:true}).fill("CityDemo-2026!");
 await page.getByRole("button",{name:"Enter workspace"}).click();
 for(const [i,level] of ["medium","high","critical"].entries()){
  const report=page.locator(".report").filter({hasText:ids[i]});
  await expect(report.locator(".priority-badge")).toHaveText(level+" priority");
  await expect(report.locator(".priority-explanation")).toBeVisible();
 }
 const reports=await page.locator(".report").allTextContents();
 const positions=ids.map(id=>reports.findIndex(text=>text.includes(id)));
 expect(positions[2]).toBeLessThan(positions[1]);expect(positions[1]).toBeLessThan(positions[0]);
});
