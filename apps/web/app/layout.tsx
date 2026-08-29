import "./globals.css";import type {Metadata} from "next";
export const metadata:Metadata={title:"RazorRecover","description":"Autonomous Revenue Recovery Intelligence"};
export default function Layout({children}:Readonly<{children:React.ReactNode}>){return <html lang="en"><body>{children}</body></html>}
