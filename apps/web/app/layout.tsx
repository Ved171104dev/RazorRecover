import "./globals.css";
import "./polish.css";
import type { Metadata } from "next";
import { ThemeToggle } from "@/components/theme-toggle";
export const metadata:Metadata={title:"RazorRecover","description":"Autonomous Revenue Recovery Intelligence"};
const themeScript = `try{const saved=localStorage.getItem("razorrecover-theme");const theme=saved==="light"||saved==="dark"?saved:"dark";document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme}catch(_){document.documentElement.dataset.theme="dark"}`;
export default function Layout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en" data-theme="dark" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html:themeScript}} /></head><body>{children}<ThemeToggle /></body></html>}
