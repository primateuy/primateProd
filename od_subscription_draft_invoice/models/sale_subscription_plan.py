from odoo import api, fields, models, _


class SaleSubscriptionPlan(models.Model):
    _inherit = "sale.subscription.plan"

    draft_invoicing = fields.Boolean(
        string='Draft Invoicing',
        help="Once this is ticked, the automatic generated"
             " invoice will be in draft state"
    )
