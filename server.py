from fastapi import FastAPI, APIRouter, Query, Request
import pandas as pd
from typing import Dict, List, Optional
import json
from datetime import datetime
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import socket
from contextlib import closing
import sys
import uvicorn

app = FastAPI()
router = APIRouter()

# Load and cache the data
DATA_PATH = Path(__file__).parent / "data" / "BCAzureUsage 1.csv"
df = pd.read_csv(DATA_PATH)
df['Date'] = pd.to_datetime(df['Date'])

# MCP Router for tools
mcp_router = APIRouter(prefix="/mcp")

@mcp_router.post("/tools/azure_usage")
async def azure_usage(request: Request) -> Dict:
    """Get a summary of Azure usage data"""
    params = await request.json()
    timeframe = params.get("timeframe", "30d")
    
    if timeframe != "all":
        days = int(timeframe.replace("d", ""))
        latest_date = df['Date'].max()
        df_filtered = df[df['Date'] >= latest_date - pd.Timedelta(days=days)]
    else:
        df_filtered = df

    service_summary = df_filtered.groupby('ServiceName').agg({
        'Quantity': 'sum',
        'Cost': 'sum'
    }).reset_index()

    return {
        "status": "success",
        "result": {
            "total_records": len(df_filtered),
            "date_range": {
                "start": df_filtered['Date'].min().strftime("%Y-%m-%d"),
                "end": df_filtered['Date'].max().strftime("%Y-%m-%d")
            },
            "total_cost": float(df_filtered['Cost'].sum()),
            "services": service_summary.to_dict('records')
        }
    }

@mcp_router.post("/tools/analyze_service")
async def analyze_service(request: Request) -> Dict:
    """Analyze costs for a specific Azure service"""
    params = await request.json()
    service_name = params.get("service_name")
    timeframe = params.get("timeframe", "30d")
    
    if not service_name:
        return {"status": "error", "message": "Service name is required"}
    
    if timeframe != "all":
        days = int(timeframe.replace("d", ""))
        latest_date = df['Date'].max()
        df_filtered = df[df['Date'] >= latest_date - pd.Timedelta(days=days)]
    else:
        df_filtered = df
        
    service_data = df_filtered[df_filtered['ServiceName'] == service_name]
    if service_data.empty:
        return {"status": "error", "message": "Service not found"}
    
    daily_costs = service_data.groupby('Date')['Cost'].sum().reset_index()
    daily_costs['MA7'] = daily_costs['Cost'].rolling(window=7).mean()
    
    return {
        "status": "success",
        "result": {
            "service": service_name,
            "total_cost": float(service_data['Cost'].sum()),
            "average_daily_cost": float(service_data['Cost'].mean()),
            "cost_trend": daily_costs.to_dict('records')
        }
    }

@mcp_router.get("/capabilities")
async def get_capabilities() -> Dict:
    """Get MCP server capabilities"""
    return {
        "version": "1.0",
        "name": "azure-monitor",
        "tools": [
            {
                "name": "azure_usage",
                "description": "Get a summary of Azure usage data",
                "parameters": {
                    "timeframe": {
                        "type": "string",
                        "description": "Time frame for analysis (e.g., '30d', 'all')",
                        "default": "30d"
                    }
                }
            },
            {
                "name": "analyze_service",
                "description": "Analyze costs for a specific Azure service",
                "parameters": {
                    "service_name": {
                        "type": "string",
                        "description": "Name of the Azure service to analyze"
                    },
                    "timeframe": {
                        "type": "string",
                        "description": "Time frame for analysis (e.g., '30d', 'all')",
                        "default": "30d"
                    }
                }
            }
        ]
    }

@router.get("/usage_summary")
async def get_usage_summary(timeframe: str = Query(default="all")) -> Dict:
    """Get a summary of Azure usage data"""
    if timeframe != "all":
        days = int(timeframe.replace("d", ""))
        latest_date = df['Date'].max()
        df_filtered = df[df['Date'] >= latest_date - pd.Timedelta(days=days)]
    else:
        df_filtered = df

    service_summary = df_filtered.groupby('ServiceName').agg({
        'Quantity': 'sum',
        'Cost': 'sum'
    }).reset_index()

    return {
        "total_records": len(df_filtered),
        "date_range": {
            "start": df_filtered['Date'].min().strftime("%Y-%m-%d"),
            "end": df_filtered['Date'].max().strftime("%Y-%m-%d")
        },
        "total_cost": float(df_filtered['Cost'].sum()),
        "services": service_summary.to_dict('records')
    }

@router.get("/cost_analysis")
async def get_cost_analysis(service: Optional[str] = None, timeframe: str = Query(default="30d")) -> Dict:
    """Get detailed cost analysis with trends"""
    if timeframe != "all":
        days = int(timeframe.replace("d", ""))
        latest_date = df['Date'].max()
        df_filtered = df[df['Date'] >= latest_date - pd.Timedelta(days=days)]
    else:
        df_filtered = df

    if service:
        df_filtered = df_filtered[df_filtered['ServiceName'] == service]

    daily_costs = df_filtered.groupby('Date').agg({
        'Cost': 'sum'
    }).reset_index()

    daily_costs['MA7'] = daily_costs['Cost'].rolling(window=7).mean()
    daily_costs['MA30'] = daily_costs['Cost'].rolling(window=30).mean()

    return {
        "daily_costs": daily_costs.to_dict('records'),
        "total_cost": float(df_filtered['Cost'].sum()),
        "avg_daily_cost": float(df_filtered['Cost'].mean()),
        "max_daily_cost": float(df_filtered.groupby('Date')['Cost'].sum().max())
    }

@router.get("/service_breakdown")
async def get_service_breakdown() -> Dict:
    """Get usage breakdown by service"""
    service_costs = df.groupby('ServiceName').agg({
        'Cost': 'sum',
        'Quantity': 'sum'
    }).reset_index().sort_values('Cost', ascending=False)
    
    return {
        "services": service_costs.to_dict('records')
    }

@router.get("/usage_patterns")
async def get_usage_patterns(service: Optional[str] = None) -> Dict:
    """Analyze usage patterns and anomalies"""
    df_filtered = df if service is None else df[df['ServiceName'] == service]
    
    daily_patterns = df_filtered.groupby(['Date', 'ServiceName']).agg({
        'Quantity': 'sum',
        'Cost': 'sum'
    }).reset_index()

    mean_cost = daily_patterns['Cost'].mean()
    std_cost = daily_patterns['Cost'].std()
    anomalies = daily_patterns[daily_patterns['Cost'] > mean_cost + 2*std_cost]

    return {
        "daily_patterns": daily_patterns.to_dict('records'),
        "anomalies": anomalies.to_dict('records'),
        "statistics": {
            "mean_daily_cost": float(mean_cost),
            "std_daily_cost": float(std_cost),
            "max_daily_cost": float(daily_patterns['Cost'].max()),
            "min_daily_cost": float(daily_patterns['Cost'].min())
        }
    }

@router.get("/recommendations")
async def get_recommendations() -> List[Dict]:
    """Generate cost optimization recommendations"""
    service_costs = df.groupby('ServiceName')['Cost'].sum().sort_values(ascending=False)
    top_services = service_costs.head(3)
    
    recommendations = []
    for service, cost in top_services.items():
        recommendations.append({
            "service": service,
            "total_cost": float(cost),
            "impact": "high" if cost > service_costs.mean() + service_costs.std() else "medium",
            "suggestion": f"Review {service} usage patterns for potential optimization"
        })

    return recommendations

# Include routers
app.include_router(router)
app.include_router(mcp_router)

def is_port_in_use(port):
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        return sock.connect_ex(('0.0.0.0', port)) == 0

def find_free_port(start_port):
    port = start_port
    while is_port_in_use(port) and port < start_port + 100:
        port += 1
    return port if not is_port_in_use(port) else None

def create_mcp_response(result, id=None):
    return {
        "jsonrpc": "2.0",
        "result": result,
        "id": id
    }

async def initialize_mcp():
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "azure-usage-monitor",
            "version": "1.0.0"
        }
    }

@mcp_router.post("/initialize")
async def mcp_initialize(request: Request):
    params = await request.json()
    if params.get("method") == "initialize":
        result = await initialize_mcp()
        return create_mcp_response(result, params.get("id"))
    return create_mcp_response({"error": "Invalid initialization request"})

if __name__ == "__main__":
    try:
        DESIRED_PORT = 8765
        PORT = find_free_port(DESIRED_PORT)
        
        if PORT is None:
            print(f"Could not find a free port in range {DESIRED_PORT}-{DESIRED_PORT + 100}", file=sys.stderr)
            sys.exit(1)
            
        if PORT != DESIRED_PORT:
            print(f"Port {DESIRED_PORT} was in use, using port {PORT} instead", file=sys.stderr)
        
        print(f"Starting Azure Usage Monitoring server with MCP support on port {PORT}...")
        
        config = uvicorn.Config(
            app, 
            host="0.0.0.0", 
            port=PORT,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
        
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)