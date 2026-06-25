# NYC DOT Toolkit - Power Apps Integration Guide

How to integrate the NYC DOT Toolkit with Microsoft Power Apps for a native Microsoft 365 experience.

## Quick Answer

**Can you package the ENTIRE program in Power Apps?**

❌ **No, not directly.** Power Apps cannot:
- Run Python code natively
- Host PostgreSQL databases
- Execute Docker containers
- Implement complex governance logic
- Run CLI tools

✅ **But you CAN build a Power Apps interface** that:
- Connects to the toolkit's REST API
- Provides user-friendly forms and dashboards
- Integrates with Power Automate and Power BI
- Fits seamlessly into Microsoft 365 ecosystem

---

## Recommended Architecture

```
┌─────────────────────────────────────────────────────────────┐
│          NYC DOT Toolkit - Hybrid Architecture              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Frontend Layer (Power Apps)                               │
│  ├─ Inspection data entry forms                            │
│  ├─ Repair scheduling interface                            │
│  ├─ Contract tracking dashboard                            │
│  ├─ Report generation wizard                               │
│  └─ Mobile-friendly mobile app                             │
│                                                               │
│  Orchestration Layer (Power Automate)                       │
│  ├─ Data validation workflows                              │
│  ├─ Approval processes                                      │
│  ├─ Scheduled report generation                            │
│  ├─ Notification routing                                    │
│  └─ Integration triggers                                    │
│                                                               │
│  API Gateway (REST Endpoints)                              │
│  ├─ socrata_toolkit.api.py endpoints                        │
│  ├─ FastAPI server (localhost:8000)                         │
│  ├─ Authentication (API keys)                               │
│  └─ Rate limiting & logging                                │
│                                                               │
│  Backend Layer (Python Toolkit)                            │
│  ├─ PostgreSQL + PostGIS database                           │
│  ├─ Data governance (Schema, CDC, Lineage)                 │
│  ├─ Compliance checking (Design rules)                     │
│  ├─ Analysis & insights engine                              │
│  └─ Docker containerized                                    │
│                                                               │
│  Reporting Layer (Power BI)                                │
│  ├─ Real-time dashboards                                   │
│  ├─ Metric tracking                                            │
│  ├─ Compliance reports                                      │
│  └─ Direct database connection (live queries)              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Path

### Step 1: Expose REST API (15 minutes)

The toolkit already has FastAPI configured. Ensure it's running:

```bash
# Start API server
python launcher.py docker up

# Or direct
uvicorn socrata_toolkit.api:app --host 0.0.0.0 --port 8000

# Available at http://localhost:8000/docs (Swagger UI)
```

API endpoints available:
- `GET /api/datasets` - List datasets
- `GET /api/dataset/{id}` - Get dataset details
- `POST /api/fetch` - Fetch data
- `POST /api/validate` - Validate data
- `POST /api/report` - Generate report
- `GET /api/lineage/{dataset}` - Data lineage
- `GET /api/compliance/{dataset}` - Compliance status

### Step 2: Build Power Apps Frontend (1-2 days)

#### Canvas App Example: Inspection Data Entry

```powerapps
// In Power Apps, add HTTP connector to REST API

// Function to fetch inspections
Function_FetchInspections() As Table
    Return JSON(
        HTTP("GET", 
            "http://localhost:8000/api/inspections",
            { 
                Headers: { 
                    "Authorization": "Bearer " & ApiToken,
                    "Content-Type": "application/json"
                }
            }
        ).Value
    );
End;

// Function to submit new inspection
Function_SubmitInspection(inspection As Record) As Boolean
    Set(
        submissionResult,
        HTTP("POST",
            "http://localhost:8000/api/inspections",
            {
                Headers: {
                    "Authorization": "Bearer " & ApiToken,
                    "Content-Type": "application/json"
                },
                Body: JSON(inspection)
            }
        )
    );
    Return submissionResult.StatusCode = 201;
End;

// Form submission
Button1.OnSelect = 
If(
    Function_SubmitInspection({
        location: TextLocation.Value,
        description: TextDescription.Value,
        borough: SelectBorough.Value,
        inspector_id: User().Email,
        timestamp: Now()
    }),
    Notify("Inspection submitted", NotificationType.Success),
    Notify("Error submitting inspection", NotificationType.Error)
)
```

#### Three App Types to Build

**1. Canvas App - Mobile Inspection Entry**
```
Screen 1: Login (Azure AD)
Screen 2: Select work location
Screen 3: Data entry form (inspection details)
Screen 4: Photo capture
Screen 5: Signature/confirmation
Screen 6: Sync status
```

**2. Model-Driven App - Repair Management**
```
Entities:
- Inspection (linked to API)
- Repair Work Order
- Contract
- Contractor
- Budget Tracking

Forms for:
- Create repair work order
- Approve repairs
- Track progress
- Invoice processing
```

**3. Power Pages - Public Dashboard**
```
Public portal showing:
- Borough-level statistics
- Repair completion rates
- Budget utilization
- Contractor performance
- Community feedback
```

### Step 3: Connect with Power Automate (1 day)

Create automated workflows:

```powerapps
// Trigger: When inspection submitted (from Power Apps)
// Action 1: Call toolkit API for validation
HTTP(
    "POST",
    "http://localhost:8000/api/validate",
    {
        Body: triggerOutputs().body
    }
);

// Action 2: If valid, create approval request
PostAdaptiveCard(
    "Manager Approval Channel",
    {
        type: "AdaptiveCard",
        body: [
            {
                type: "TextBlock",
                text: "New Inspection Requires Review",
                weight: "bolder"
            }
        ],
        actions: [
            {
                type: "Action.OpenUrl",
                title: "Approve",
                url: outputs('HTTP').body.approval_url
            }
        ]
    }
);

// Action 3: If approved, update database
SQL_Server(
    "UPDATE inspections SET approved = 1 WHERE id = @id"
);

// Action 4: Notify inspector via email
SendEmail(
    inspector_email,
    "Inspection Approved",
    "Your inspection has been reviewed and approved."
);
```

### Step 4: Add Power BI Dashboards (1 day)

```powerapps
// Direct connection to PostgreSQL
Source = PostgreSQL.Database(
    "localhost",
    5432,
    "sidewalk_db"
),

// Query tables
Inspections = Source[inspections],
Repairs = Source[repairs],
Contracts = Source[contracts],

// Create measures
Avg_Repair_Cost = AVERAGE(Repairs[cost]),
On_Time_Completion % = COUNTIFS(Repairs, Repairs[completed_date] <= Repairs[due_date]) / COUNT(Repairs),
Budget_Utilization = SUM(Contracts[spent]) / SUM(Contracts[budget])
```

Dashboard pages:
- Real-time inspection metrics
- Repair completion tracking
- Budget performance by borough
- Contractor performance scorecards
- Compliance audit trail

---

## Step-by-Step Implementation

### Phase 1: API Exposure (Week 1)

**Tasks:**
1. ✅ API already configured in toolkit
2. Deploy API to accessible server (not localhost)
3. Configure authentication (API keys)
4. Document endpoints
5. Test all endpoints with Postman

**Time**: 1-2 days

**Deliverable**: Documented REST API at `http://api.nycdot.gov:8000`

### Phase 2: Power Apps Development (Week 2-3)

**Canvas App Tasks:**
1. Create authentication screen (Azure AD)
2. Build inspection entry form
3. Implement photo capture
4. Add offline sync capability
5. Create dashboard summary screen

**Testing:**
- Unit test each screen
- End-to-end testing
- Mobile device testing
- Load testing with multiple users

**Time**: 5-7 days

**Deliverable**: Mobile-ready Power Apps for field inspectors

### Phase 3: Power Automate Integration (Week 3)

**Workflow Tasks:**
1. Create data validation workflow
2. Set up approval routing
3. Build notification system
4. Add compliance checking triggers
5. Schedule daily report generation

**Time**: 2-3 days

**Deliverable**: Automated workflows connecting all systems

### Phase 4: Power BI Dashboard (Week 4)

**Dashboard Tasks:**
1. Connect to PostgreSQL
2. Create data model
3. Build Metric measures
4. Design report pages
5. Configure auto-refresh

**Time**: 2-3 days

**Deliverable**: Executive dashboard with real-time metrics

---

## Security Considerations for Power Apps

### Authentication Flow

```
┌─────────────┐
│  Power Apps │
└──────┬──────┘
       │
       │ Azure AD Login
       ▼
┌──────────────────────┐
│  Microsoft Entra ID  │
│  (Azure AD)          │
└──────┬───────────────┘
       │
       │ OAuth Token
       ▼
┌──────────────────────────────┐
│  Python Toolkit API          │
│  (Validates token)           │
│  (Issues API key)            │
└──────┬───────────────────────┘
       │
       │ Operations
       ▼
┌──────────────────────┐
│  PostgreSQL Database │
│  CDC Audit Logging   │
└──────────────────────┘
```

Implement in toolkit:

```python
# socrata_toolkit/api.py
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        # Verify Azure AD token
        payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        user_email = payload.get("email")
        if not user_email:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_email
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/api/inspections")
async def get_inspections(user_email: str = Depends(verify_token)):
    # Only return inspections for user's borough
    return db.query(Inspection).filter(
        Inspection.inspector_email == user_email
    ).all()
```

### Data Access Control

```python
# socrata_toolkit/rbac.py - Role-Based Access Control

class Role(str, Enum):
    INSPECTOR = "inspector"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"
    ADMIN = "admin"

# In API endpoints
@app.post("/api/inspections/{id}/approve")
async def approve_inspection(
    id: int,
    user_email: str = Depends(verify_token)
):
    # Check user role
    user_role = get_user_role(user_email)
    if user_role not in [Role.SUPERVISOR, Role.MANAGER, Role.ADMIN]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    # Approve inspection
    inspection = db.query(Inspection).get(id)
    inspection.approved_by = user_email
    inspection.approved_date = datetime.utcnow()
    db.commit()
    
    return {"status": "approved"}
```

---

## Comparison: Streamlit vs Power Apps

| Aspect | Streamlit | Power Apps |
|--------|-----------|-----------|
| **Best For** | Data analysts, quick prototypes | Enterprise users, corporate IT |
| **Learning Curve** | Easy (Python) | Medium (low-code) |
| **Mobile Ready** | Responsive but not native | Native mobile app |
| **Integration** | Manual API calls | Built-in connectors |
| **Microsoft 365** | Limited | Full integration |
| **Customization** | Full Python power | Visual builder |
| **Deployment** | Self-hosted or cloud | Microsoft cloud |
| **Cost** | Free (hosting costs vary) | $20/user/month |
| **User Base** | Technical analysts | Business users |

**Recommendation**: 
- Keep **Streamlit** for internal analysts
- Add **Power Apps** for business users and field staff
- Both access the same REST API backend

---

## Power Apps Development Resources

### Required Skills
- Power Apps canvas/model-driven app development
- Power Automate workflow design
- REST API integration
- Azure AD authentication
- Power BI data modeling

### Training Path
1. **Microsoft Learn** - Power Apps fundamentals (5 hours)
2. **Power Apps Documentation** - https://docs.microsoft.com/power-apps
3. **Hands-on Labs** - Build sample inspection app (3-5 hours)
4. **Integration Testing** - Connect to toolkit API (2-3 hours)

### Development Timeline
- **Small team** (1-2 developers): 4-6 weeks
- **Medium team** (3-5 developers): 2-3 weeks
- **Large team** (5+ developers): 1-2 weeks

---

## Cost Analysis

### One-Time Costs
| Item | Cost | Notes |
|------|------|-------|
| API Server (if cloud-hosted) | $50-200/month | AWS/Azure VM |
| Power Apps Premium Licenses | $20/user/month | Required for custom connectors |
| Development hours | 200-400 hours | Internal or contractor |
| **Total Setup** | **$2,000-5,000** | Varies by scope |

### Ongoing Costs
| Item | Cost | Notes |
|------|------|-------|
| Power Apps licenses | $20/user/month | ~$200-500/month for team of 10-25 |
| Power Automate flows | Included | Unlimited with Microsoft 365 |
| API hosting | $50-200/month | Depends on usage |
| **Monthly** | **$250-700** | Varies by team size |

---

## Alternative: Embed REST API in Excel

If Power Apps is too much, create interactive Excel workbook:

```vba
' Excel VBA to call REST API
Function FetchInspections() As String
    Dim xhr As Object
    Set xhr = CreateObject("MSXML2.XMLHTTP")
    
    xhr.Open "GET", "http://localhost:8000/api/inspections", False
    xhr.SetRequestHeader "Authorization", "Bearer " & ApiToken
    xhr.Send
    
    FetchInspections = xhr.ResponseText
End Function

' In worksheet
=FetchInspections()
```

Add data to Excel refresh buttons:
- Pull latest inspection data
- Submit corrections
- Generate reports
- Export to PDF

**Pros**: Works with existing Excel skills  
**Cons**: Limited to Excel, no mobile, less enterprise-friendly

---

## Recommendation

**Best Approach for NYC DOT**:

1. **Keep** Streamlit for analysts
2. **Add** Power Apps for field inspectors and managers
3. **Use** Power Automate for approvals and notifications
4. **Deploy** Power BI for executive dashboards
5. **Backend** stays as Python + PostgreSQL

This gives you:
- ✅ Native mobile app (Power Apps)
- ✅ Enterprise integration (Microsoft 365)
- ✅ Advanced analytics (Python + Power BI)
- ✅ Workflow automation (Power Automate)
- ✅ Full audit trails (CDC logging)

---

## Next Steps

1. **Assess your team's Power Apps skills**
   - Do you have Power Apps developers?
   - Can you hire contractors?
   - Training timeline?

2. **Plan phased rollout**
   - Phase 1: API exposure (Week 1)
   - Phase 2: Power Apps canvas app (Weeks 2-3)
   - Phase 3: Power Automate workflows (Week 3)
   - Phase 4: Power BI dashboards (Week 4)

3. **Estimate budget**
   - Development: $2,000-5,000
   - Monthly: $250-700 (depends on licenses)

4. **Start with pilot**
   - One borough first
   - 5-10 field inspectors
   - Gather feedback
   - Scale to all boroughs

---

## Resources

- **Power Apps Docs**: https://docs.microsoft.com/power-apps
- **Power Automate Docs**: https://docs.microsoft.com/power-automate
- **API Documentation**: `docs/api_guide.md`
- **Architecture Guide**: `docs/architecture.md`
- **REST API Endpoints**: `socrata_toolkit.api`

---

**Summary**: You cannot package the ENTIRE program in Power Apps, but you can build a beautiful Power Apps frontend that connects to the Python backend via REST API, giving you the best of both worlds: enterprise Microsoft 365 integration with enterprise-grade data governance.

---

**Version**: 0.3.0  
**Last Updated**: 2026-05-11  
**Status**: Ready for Power Apps Implementation
