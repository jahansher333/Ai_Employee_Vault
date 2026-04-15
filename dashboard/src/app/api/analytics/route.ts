import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { vaultPath } from "@/lib/vault";

export const dynamic = "force-dynamic";

interface Transaction {
  date: string;
  description: string;
  amount: number;
  category: string;
}

function parseCSV(content: string): Transaction[] {
  const lines = content.trim().split("\n");
  if (lines.length < 2) return [];

  const header = lines[0].toLowerCase().split(",").map((h) => h.trim());
  const dateIdx = header.findIndex((h) => ["date", "transaction_date", "order_date"].includes(h));
  const descIdx = header.findIndex((h) => ["description", "memo", "payee", "product", "item", "name"].includes(h));
  const amountIdx = header.findIndex((h) => ["amount", "value", "total", "total_sales", "total_amount", "revenue", "sales", "price", "unit_price"].includes(h));
  const catIdx = header.findIndex((h) => ["category", "type", "class", "department", "region"].includes(h));

  if (amountIdx === -1) return [];

  const transactions: Transaction[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(",").map((c) => c.trim());
    const amount = parseFloat(cols[amountIdx]);
    if (isNaN(amount)) continue;
    transactions.push({
      date: dateIdx >= 0 ? cols[dateIdx] : "",
      description: descIdx >= 0 ? cols[descIdx] : "(No description)",
      amount,
      category: catIdx >= 0 ? cols[catIdx] || "Uncategorized" : "Uncategorized",
    });
  }
  return transactions;
}

// POST: analyze uploaded/pasted CSV data and optionally save to Accounting/
export async function POST(request: Request) {
  const body = await request.json();
  const csvContent: string = body.csv || "";
  const saveAs: string = body.save_as || "";

  if (!csvContent.trim()) {
    return NextResponse.json({ success: false, error: "No CSV data provided" }, { status: 400 });
  }

  const transactions = parseCSV(csvContent);
  if (transactions.length === 0) {
    return NextResponse.json({
      success: false,
      error: "Could not parse CSV. Ensure columns include: date, description, amount, category",
    }, { status: 400 });
  }

  // Optionally save to Accounting/ folder
  if (saveAs) {
    const accountingDir = vaultPath("Accounting");
    if (!fs.existsSync(accountingDir)) fs.mkdirSync(accountingDir, { recursive: true });
    const safeName = saveAs.replace(/[^a-zA-Z0-9_-]/g, "_").replace(/\.csv$/, "") + ".csv";
    fs.writeFileSync(path.join(accountingDir, safeName), csvContent, "utf-8");
  }

  // Run same analysis logic
  const totalRevenue = transactions.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const totalExpenses = transactions.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
  const netIncome = totalRevenue - totalExpenses;

  const monthly: Record<string, { revenue: number; expenses: number; count: number }> = {};
  for (const t of transactions) {
    const month = t.date ? t.date.substring(0, 7) : "Unknown";
    if (!monthly[month]) monthly[month] = { revenue: 0, expenses: 0, count: 0 };
    if (t.amount > 0) monthly[month].revenue += t.amount;
    else monthly[month].expenses += Math.abs(t.amount);
    monthly[month].count++;
  }
  const monthlyBreakdown = Object.entries(monthly)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([m, d]) => ({
      month: m,
      revenue: Math.round(d.revenue * 100) / 100,
      expenses: Math.round(d.expenses * 100) / 100,
      net: Math.round((d.revenue - d.expenses) * 100) / 100,
      transaction_count: d.count,
    }));

  const categories: Record<string, { total: number; count: number }> = {};
  for (const t of transactions) {
    if (!categories[t.category]) categories[t.category] = { total: 0, count: 0 };
    categories[t.category].total += t.amount;
    categories[t.category].count++;
  }
  const categoryBreakdown = Object.entries(categories)
    .map(([cat, d]) => ({ category: cat, total: Math.round(d.total * 100) / 100, count: d.count, type: d.total >= 0 ? "revenue" : "expense" }))
    .sort((a, b) => Math.abs(b.total) - Math.abs(a.total));

  const topExpenses = transactions
    .filter((t) => t.amount < 0)
    .sort((a, b) => a.amount - b.amount)
    .slice(0, 5)
    .map((t) => ({ date: t.date, description: t.description, amount: Math.abs(t.amount), category: t.category }));

  const catAverages: Record<string, { sum: number; count: number }> = {};
  for (const t of transactions) {
    if (!catAverages[t.category]) catAverages[t.category] = { sum: 0, count: 0 };
    catAverages[t.category].sum += Math.abs(t.amount);
    catAverages[t.category].count++;
  }
  const anomalies: object[] = [];
  for (const t of transactions) {
    const avg = catAverages[t.category];
    if (avg.count < 2) continue;
    const catAvg = avg.sum / avg.count;
    const absAmount = Math.abs(t.amount);
    if (absAmount > 2 * catAvg) {
      anomalies.push({
        date: t.date, description: t.description, amount: t.amount, category: t.category,
        category_avg: Math.round(catAvg * 100) / 100, ratio: Math.round((absAmount / catAvg) * 10) / 10,
      });
    }
  }

  return NextResponse.json({
    success: true,
    total_revenue: Math.round(totalRevenue * 100) / 100,
    total_expenses: Math.round(totalExpenses * 100) / 100,
    net_income: Math.round(netIncome * 100) / 100,
    transaction_count: transactions.length,
    monthly_breakdown: monthlyBreakdown,
    category_breakdown: categoryBreakdown,
    top_expenses: topExpenses,
    anomalies,
    files_analyzed: saveAs ? [saveAs] : ["(uploaded data)"],
    generated_at: new Date().toISOString(),
    saved: !!saveAs,
  });
}

export function GET() {
  const accountingDir = vaultPath("Accounting");

  if (!fs.existsSync(accountingDir)) {
    return NextResponse.json({
      success: false,
      error: "No Accounting/ folder found",
      total_revenue: 0, total_expenses: 0, net_income: 0,
      monthly_breakdown: [], top_expenses: [], anomalies: [],
      category_breakdown: [], files_analyzed: [],
    });
  }

  const csvFiles = fs.readdirSync(accountingDir).filter((f) => f.endsWith(".csv"));
  if (csvFiles.length === 0) {
    return NextResponse.json({
      success: false,
      error: "No CSV files in Accounting/",
      total_revenue: 0, total_expenses: 0, net_income: 0,
      monthly_breakdown: [], top_expenses: [], anomalies: [],
      category_breakdown: [], files_analyzed: [],
    });
  }

  // Read all CSV files
  let allTransactions: Transaction[] = [];
  for (const file of csvFiles) {
    const content = fs.readFileSync(path.join(accountingDir, file), "utf-8");
    allTransactions = allTransactions.concat(parseCSV(content));
  }

  // Calculate totals
  const totalRevenue = allTransactions.filter((t) => t.amount > 0).reduce((s, t) => s + t.amount, 0);
  const totalExpenses = allTransactions.filter((t) => t.amount < 0).reduce((s, t) => s + Math.abs(t.amount), 0);
  const netIncome = totalRevenue - totalExpenses;

  // Monthly breakdown
  const monthly: Record<string, { revenue: number; expenses: number; count: number }> = {};
  for (const t of allTransactions) {
    const month = t.date ? t.date.substring(0, 7) : "Unknown";
    if (!monthly[month]) monthly[month] = { revenue: 0, expenses: 0, count: 0 };
    if (t.amount > 0) monthly[month].revenue += t.amount;
    else monthly[month].expenses += Math.abs(t.amount);
    monthly[month].count++;
  }
  const monthlyBreakdown = Object.entries(monthly)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, data]) => ({
      month,
      revenue: Math.round(data.revenue * 100) / 100,
      expenses: Math.round(data.expenses * 100) / 100,
      net: Math.round((data.revenue - data.expenses) * 100) / 100,
      transaction_count: data.count,
    }));

  // Category breakdown
  const categories: Record<string, { total: number; count: number }> = {};
  for (const t of allTransactions) {
    if (!categories[t.category]) categories[t.category] = { total: 0, count: 0 };
    categories[t.category].total += t.amount;
    categories[t.category].count++;
  }
  const categoryBreakdown = Object.entries(categories)
    .map(([category, data]) => ({
      category,
      total: Math.round(data.total * 100) / 100,
      count: data.count,
      type: data.total >= 0 ? "revenue" : "expense",
    }))
    .sort((a, b) => Math.abs(b.total) - Math.abs(a.total));

  // Top 5 expenses
  const topExpenses = allTransactions
    .filter((t) => t.amount < 0)
    .sort((a, b) => a.amount - b.amount)
    .slice(0, 5)
    .map((t) => ({
      date: t.date,
      description: t.description,
      amount: Math.abs(t.amount),
      category: t.category,
    }));

  // Anomaly detection: transactions > 2x category average
  const catAverages: Record<string, { sum: number; count: number }> = {};
  for (const t of allTransactions) {
    if (!catAverages[t.category]) catAverages[t.category] = { sum: 0, count: 0 };
    catAverages[t.category].sum += Math.abs(t.amount);
    catAverages[t.category].count++;
  }

  const anomalies: object[] = [];
  for (const t of allTransactions) {
    const avg = catAverages[t.category];
    if (avg.count < 2) continue;
    const catAvg = avg.sum / avg.count;
    const absAmount = Math.abs(t.amount);
    if (absAmount > 2 * catAvg) {
      anomalies.push({
        date: t.date,
        description: t.description,
        amount: t.amount,
        category: t.category,
        category_avg: Math.round(catAvg * 100) / 100,
        ratio: Math.round((absAmount / catAvg) * 10) / 10,
      });
    }
  }

  return NextResponse.json({
    success: true,
    total_revenue: Math.round(totalRevenue * 100) / 100,
    total_expenses: Math.round(totalExpenses * 100) / 100,
    net_income: Math.round(netIncome * 100) / 100,
    transaction_count: allTransactions.length,
    monthly_breakdown: monthlyBreakdown,
    category_breakdown: categoryBreakdown,
    top_expenses: topExpenses,
    anomalies,
    files_analyzed: csvFiles,
    generated_at: new Date().toISOString(),
  });
}
