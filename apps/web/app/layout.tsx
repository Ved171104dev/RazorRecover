import "./globals.css";
import "./polish.css";
import type { Metadata } from "next";
import { ThemeToggle } from "@/components/theme-toggle";
import { ApiWarmup } from "@/components/api-warmup";
export const metadata:Metadata={title:"RazorRecover","description":"Autonomous Revenue Recovery Intelligence",icons:{icon:[{url:"/icon.svg",type:"image/svg+xml"}],shortcut:"/icon.svg"}};
const themeScript = `try{const saved=localStorage.getItem("razorrecover-theme");const theme=saved==="light"||saved==="dark"?saved:"dark";document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme}catch(_){document.documentElement.dataset.theme="dark"}`;
export default function Layout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en" data-theme="dark" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:themeScript}} /></head><body><ApiWarmup />{children}<ThemeToggle /></body></html>}
