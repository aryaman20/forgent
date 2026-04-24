from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_org, get_current_user
from app.core.database import get_db
from app.services.billing_service import billing_service


class CheckoutRequest(BaseModel):
	plan: str
	success_url: str
	cancel_url: str


router = APIRouter()


@router.post("/checkout", response_model=dict)
async def create_checkout(
	data: CheckoutRequest,
	db: AsyncSession = Depends(get_db),
	current_user=Depends(get_current_user),
	current_org=Depends(get_current_org),
):
	if data.plan not in {"pro", "team"}:
		raise HTTPException(status_code=400, detail="Invalid plan. Must be 'pro' or 'team'.")

	url = await billing_service.create_checkout_session(
		db,
		current_org,
		current_org.plan,
		current_user.email,
		data.success_url,
		data.cancel_url,
	)
	return {"checkout_url": url}


@router.post("/portal", response_model=dict)
async def create_portal(
	current_user=Depends(get_current_user),
	current_org=Depends(get_current_org),
):
	_ = current_user
	url = await billing_service.create_portal_session(
		current_org,
		return_url="http://localhost:3000/dashboard/billing",
	)
	return {"portal_url": url}


@router.post("/webhook", response_model=dict)
async def stripe_webhook(
	request: Request,
	db: AsyncSession = Depends(get_db),
):
	payload = await request.body()
	sig_header = request.headers.get("stripe-signature", "")

	await billing_service.handle_webhook(db, payload, sig_header)
	return {"status": "ok"}
