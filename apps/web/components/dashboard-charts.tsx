"use client";

import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { inr, label } from "@/lib/api";

const causeColors = ["#e3ad49", "#c89447", "#a97c42", "#876438", "#665031"];

function compactInr(valuePaise: number) {
  const rupees = valuePaise / 100;
  if (rupees >= 100000) {
    const lakhs = rupees / 100000;
    return `₹${lakhs >= 10 ? Math.round(lakhs) : lakhs.toFixed(1)}L`;
  }
  if (rupees >= 1000) return `₹${Math.round(rupees / 1000)}K`;
  return `₹${Math.round(rupees)}`;
}

export function RecoveryChart({ data }: { data: Array<Record<string, unknown>> }) {
  return <div className="chart"><ResponsiveContainer><AreaChart data={data}><defs><linearGradient id="gold" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#d6a34a" stopOpacity=".4" /><stop offset="1" stopColor="#d6a34a" stopOpacity="0" /></linearGradient></defs><CartesianGrid stroke="var(--line)" vertical={false} /><XAxis dataKey="day" stroke="var(--muted)" /><YAxis stroke="var(--muted)" tickFormatter={(value) => `₹${Math.round(Number(value) / 100000)}k`} /><Tooltip formatter={(value) => inr(Number(value))} /><Area dataKey="recovered_paise" stroke="#d6a34a" fill="url(#gold)" /></AreaChart></ResponsiveContainer></div>;
}

export function RootCauseChart({ data }: { data: Array<Record<string, unknown>> }) {
  return <div className="chart rootCauseChart"><ResponsiveContainer><BarChart data={data} margin={{ top: 28, right: 20, left: 6, bottom: 2 }} barCategoryGap="24%"><CartesianGrid stroke="var(--line)" strokeDasharray="4 7" vertical={false} /><XAxis dataKey="name" axisLine={false} tickLine={false} tickMargin={13} tick={{ fill: "var(--muted)", fontSize: 12 }} tickFormatter={(value) => label(String(value))} /><YAxis axisLine={false} tickLine={false} width={58} tick={{ fill: "var(--muted)", fontSize: 12 }} tickFormatter={(value) => compactInr(Number(value))} /><Tooltip cursor={{ fill: "rgba(226,173,72,.045)" }} contentStyle={{ background: "var(--panel2)", border: "1px solid var(--border)", borderRadius: 12, boxShadow: "0 14px 36px rgba(0,0,0,.32)" }} labelStyle={{ color: "var(--text)", fontWeight: 700, marginBottom: 6 }} itemStyle={{ color: "var(--accent)" }} labelFormatter={(value) => label(String(value))} formatter={(value) => [inr(Number(value)), "Revenue at risk"]} /><Bar dataKey="value_paise" radius={[8, 8, 2, 2]} maxBarSize={92}>{data.map((_, index) => <Cell key={index} fill={causeColors[index % causeColors.length]} />)}<LabelList dataKey="value_paise" position="top" formatter={(value: unknown) => compactInr(Number(value))} fill="var(--text)" fontSize={12} fontWeight={700} /></Bar></BarChart></ResponsiveContainer></div>;
}