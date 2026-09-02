// Local development sets NEXT_PUBLIC_API_URL to the FastAPI port. In hosted
// environments requests remain same-origin and Next.js proxies /api to FastAPI.
export const API=process.env.NEXT_PUBLIC_API_URL??"";
function cookie(name:string){if(typeof document==="undefined")return "";return document.cookie.split("; ").find(x=>x.startsWith(name+"="))?.split("=")[1]||""}
function errorMessage(body:any):string{
 const detail=body?.error?.message??body?.detail;
 if(typeof detail==="string")return detail;
 if(Array.isArray(detail))return detail.map((item:any)=>item?.msg||item?.message||"Invalid input").join("; ");
 if(detail&&typeof detail.message==="string")return detail.message;
 return "Request failed";
}
export async function api<T=any>(path:string,options:RequestInit={}):Promise<T>{
 const mutation=!!options.method&&options.method!=="GET";const form=typeof FormData!=="undefined"&&options.body instanceof FormData;const headers:Record<string,string>={...(form?{}:{"Content-Type":"application/json"}),...((options.headers||{}) as Record<string,string>)};
 if(mutation)headers["X-CSRF-Token"]=decodeURIComponent(cookie("rr_csrf"));
 let r:Response;try{r=await fetch(API+path,{...options,headers,credentials:"include",cache:"no-store"})}catch{throw new Error(typeof navigator!=="undefined"&&!navigator.onLine?"You are offline. Reconnect and try again.":"Unable to reach the service. It may still be waking up; please try again shortly.")}
 const body=await r.json().catch(()=>({detail:r.status>=500?"The service is temporarily unavailable. Please try again.":"Request failed"}));if(!r.ok)throw new Error(errorMessage(body));return body as T;
}
export const inr=(paise:number)=>new Intl.NumberFormat("en-IN",{style:"currency",currency:"INR",maximumFractionDigits:0}).format((paise||0)/100);
export const label=(s:string)=>s.replaceAll("_"," ").replace(/\b\w/g,x=>x.toUpperCase());
