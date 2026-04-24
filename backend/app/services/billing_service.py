import uuid

import stripe
import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import Organization, PlanType

stripe.api_key = settings.STRIPE_SECRET_KEY

STRIPE_PRICES = {
    "pro": "price_pro_monthly",
    "team": "price_team_monthly",
}

logger = structlog.get_logger()


class BillingService:
    async def get_or_create_stripe_customer(
        self,
        db: AsyncSession,
        org: Organization,
        email: str,
    ) -> str:
        if org.stripe_customer_id:
            return org.stripe_customer_id

        customer = stripe.Customer.create(
            email=email,
            name=org.name,
            metadata={"org_id": str(org.id)},
        )

        org.stripe_customer_id = customer.id
        await db.flush()
        return customer.id

    async def create_checkout_session(
        self,
        db: AsyncSession,
        org: Organization,
        plan: str,
        email: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        customer_id = await self.get_or_create_stripe_customer(db, org, email)
        price_id = STRIPE_PRICES[plan]

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"org_id": str(org.id), "plan": plan},
        )

        return session.url

    async def create_portal_session(self, org: Organization, return_url: str) -> str:
        session = stripe.billing_portal.Session.create(
            customer=org.stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    async def handle_webhook(self, db: AsyncSession, payload: bytes, sig_header: str) -> dict:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.error.SignatureVerificationError) as exc:
            raise HTTPException(status_code=400, detail="Invalid Stripe webhook signature") from exc

        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            metadata = data_object.get("metadata", {}) or {}
            org_id = metadata.get("org_id")
            plan = metadata.get("plan")

            if org_id and plan in STRIPE_PRICES:
                result = await db.execute(
                    select(Organization).where(Organization.id == uuid.UUID(org_id))
                )
                org = result.scalar_one_or_none()
                if org:
                    if plan == "pro":
                        org.plan = PlanType.PRO
                    elif plan == "team":
                        org.plan = PlanType.TEAM
                    await db.flush()
                    logger.info("Organization upgraded", org_id=org_id, plan=plan)

        elif event_type == "customer.subscription.deleted":
            customer_id = data_object.get("customer")
            if customer_id:
                result = await db.execute(
                    select(Organization).where(Organization.stripe_customer_id == customer_id)
                )
                org = result.scalar_one_or_none()
                if org:
                    org.plan = PlanType.FREE
                    await db.flush()
                    logger.info("Organization downgraded", org_id=str(org.id), plan="free")

        return {"status": "handled"}


billing_service = BillingService()
