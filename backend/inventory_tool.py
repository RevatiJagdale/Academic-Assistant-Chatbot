# backend/inventory_tool.py
import pandas as pd
import os

DATA_PATH = "data/inventory.xlsx"

class InventoryTool:
    def __init__(self, file_path=DATA_PATH):
        if not os.path.exists(file_path):
            print(f"[ERROR] Inventory file not found at {file_path}")
            self.df = pd.DataFrame()
        else:
            self.df = pd.read_excel(file_path, dtype=str).fillna("")
            self.df.columns = self.df.columns.str.strip().str.lower()
            # Convert quantity to numeric for summing
            self.df['quantity'] = pd.to_numeric(self.df['quantity'], errors='coerce').fillna(0)
            print("[InventoryTool] Loaded successfully.")

    def query_inventory(self, question: str) -> str:
        if self.df.empty:
            return "Inventory data is missing. Please upload inventory.xlsx."
            
        q_lower = question.lower()
        
        # --- Intent 1: Get Total Quantity ---
        if "how many" in q_lower:
            # Extract item name
            item = q_lower.split("how many")[-1].strip("? .s")
            if "total" in item:
                item = item.replace("total", "").strip()

            results = self.df[self.df['equipmentname'].str.contains(item, case=False)]
            if results.empty:
                return f"No items matching '{item}' found in inventory."
            
            total_qty = results['quantity'].sum()
            return f"Total quantity for '{item}': {total_qty} units."

        # --- Intent 2: Check Location / Availability ---
        if "where are" in q_lower or "location of" in q_lower:
            item = q_lower.split("are the")[-1].split("location of")[-1].strip("? .s")
            results = self.df[self.df['equipmentname'].str.contains(item, case=False)]
            if results.empty:
                return f"No items matching '{item}' found."
            
            report = f"Location(s) for '{item}':\n"
            for _, row in results.iterrows():
                report += f"- {row['quantity']} units in {row['location']} ({row['condition']} condition)\n"
            return report
            
        # --- Intent 3: Check Condition ---
        if "condition of" in q_lower:
            item = q_lower.split("condition of the")[-1].strip("? .s")
            results = self.df[self.df['equipmentname'].str.contains(item, case=False)]
            if results.empty:
                return f"No items matching '{item}' found."
            
            report = f"Condition for '{item}':\n"
            for _, row in results.iterrows():
                report += f"- {row['location']}: {row['condition']}\n"
            return report

        return "I can answer 'how many', 'where are', or 'condition of' equipment."