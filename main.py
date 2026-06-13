from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import List
import datetime as dt

from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# This creates a local file named 'finance.db' right inside your project folder
DATABASE_URL = "sqlite:///./finance.db"

# connect_args={"check_same_thread": False} is required exclusively for SQLite
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQLALCHEMY MODELS (Database Tables) ---
class UserModel(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True)
    password = Column(String)

class ExpenseModel(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, index=True)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(String)
    date = Column(Date, default=dt.date.today)

class BudgetModel(Base):
    __tablename__ = "budgets"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, index=True)
    category = Column(String, nullable=False)
    monthly_limit = Column(Float, nullable=False)

# Create the actual database file and tables automatically
Base.metadata.create_all(bind=engine)

# --- FASTAPI APPLICATION INIT ---
app = FastAPI(title="Personal Finance Tracker (SQLite Powered)")

# --- DATABASE DEPENDENCY ---
# This opens a connection to the database for every request and closes it safely when done
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- SECURITY HELPER ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user.username

# --- PYDANTIC SCHEMAS ---
class UserRegister(BaseModel):
    username: str
    password: str

class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0)
    category: str
    description: str

class ExpenseResponse(ExpenseCreate):
    id: int
    username: str
    date: dt.date
    class Config:
        from_attributes = True

class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float = Field(..., gt=0)

# --- ROUTES (Interacting with SQLite via SQLAlchemy) ---

# 1. USER AUTHENTICATION
@app.post("/register", status_code=status.HTTP_201_CREATED, tags=["Auth"])
def register(user: UserRegister, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = UserModel(username=user.username, password=user.password)
    db.add(new_user)
    db.commit() # Saves permanently to finance.db
    return {"message": "User registered successfully"}

@app.post("/token", tags=["Auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.username == form_data.username).first()
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": user.username, "token_type": "bearer"}


# 2. EXPENSE TRACKING
@app.post("/expenses", response_model=ExpenseResponse, tags=["Expenses"])
def add_expense(expense: ExpenseCreate, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    new_expense = ExpenseModel(
        username=current_user,
        amount=expense.amount,
        category=expense.category,
        description=expense.description
    )
    db.add(new_expense)
    db.commit() # Saves permanently to finance.db
    db.refresh(new_expense)
    return new_expense

@app.get("/expenses", response_model=List[ExpenseResponse], tags=["Expenses"])
def get_expenses(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(ExpenseModel).filter(ExpenseModel.username == current_user).all()


# 3. BUDGETING
@app.post("/budgets", tags=["Budgeting"])
def set_budget(budget: BudgetCreate, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if a budget for this category already exists, if so update it, otherwise create it
    existing_budget = db.query(BudgetModel).filter(
        BudgetModel.username == current_user, 
        BudgetModel.category == budget.category
    ).first()
    
    if existing_budget:
        existing_budget.monthly_limit = budget.monthly_limit
    else:
        new_budget = BudgetModel(username=current_user, category=budget.category, monthly_limit=budget.monthly_limit)
        db.add(new_budget)
        
    db.commit() # Saves permanently to finance.db
    return {"message": f"Budget for '{budget.category}' set to ${budget.monthly_limit}"}


# 4. ANALYTICS & WARNINGS
@app.get("/analytics", tags=["Analytics"])
def get_analytics(current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    user_budgets = db.query(BudgetModel).filter(BudgetModel.username == current_user).all()
    user_expenses = db.query(ExpenseModel).filter(ExpenseModel.username == current_user).all()
    
    # Calculate total spending by category
    spending_by_category = {}
    for exp in user_expenses:
        spending_by_category[exp.category] = spending_by_category.get(exp.category, 0.0) + exp.amount
    
    report = {}
    warnings = []
    
    for b in user_budgets:
        spent = spending_by_category.get(b.category, 0.0)
        remaining = b.monthly_limit - spent
        
        report[b.category] = {
            "budget_limit": b.monthly_limit,
            "total_spent": spent,
            "remaining_balance": remaining
        }
        
        if spent > b.monthly_limit:
            warnings.append(f"⚠️ OVER BUDGET ALERT: You have exceeded your '{b.category}' budget by ${abs(remaining):.2f}!")
            
    return {
        "user": current_user,
        "category_reports": report,
        "warnings": warnings if warnings else ["✅ All clear! You are within your budget limits."]
    }
# --- ADD THESE NEW ROUTE ENDPOINTS TO YOUR main.py ---

@app.delete("/budgets/{category}")
def delete_specific_budget(category: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    budget = db.query(Budget).filter(Budget.category == category, Budget.user_id == current_user.id).first()
    if not budget:
        raise HTTPException(status_code=404, detail="Budget category not found")
    
    db.delete(budget)
    db.commit()
    return {"message": f"Successfully deleted budget for {category}"}


@app.delete("/budgets")
def delete_all_budgets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Budget).filter(Budget.user_id == current_user.id).delete()
    db.commit()
    return {"message": "All budgets have been successfully reset"}