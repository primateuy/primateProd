from odoo import models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _process_auto_invoice(self, invoice):
        if not self.plan_id.draft_invoicing:
            return super()._process_auto_invoice(invoice)
