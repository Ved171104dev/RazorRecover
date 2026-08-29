import {describe,expect,it} from "vitest";import {inr,label} from "./api";
describe("display helpers",()=>{it("converts paise only at display boundary",()=>expect(inr(349900)).toContain("3,499"));it("labels states",()=>expect(label("awaiting_approval")).toBe("Awaiting Approval"))});
