import hashlib, hmac, requests

from werkzeug import urls

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare

import logging

_logger = logging.getLogger(__name__)


class PaymentAcquirerIpayOdoo(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('ipay', 'Ipay')], ondelete={'ipay': 'set default'})
    _ipay_key = fields.Char('Ipay Key', groups='base.group_user')
    _ipay_vendor_id = fields.Char('Vendor ID', groups='base.group_user')
    _ipay_live = fields.Boolean('Live', groups='base.group_user')
    _autopay = fields.Boolean("autopay", groups='base.group_user')

    def _get_ipay_urls(self, environment):
        if environment == "prod":
            return 'https://payments.ipayafrica.com/v3/ke'
        else:
            return 'https://payments.ipayafrica.com/v3/ke'

    def ipay_form_generate_values(self, values):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        key1 = self._ipay_key

        ph = values.get('partner_phone')
        if ph == "":
            phone = values.get('billing_partner_phone')
        else:
            phone = ph

        ipay_values = dict(values,
                                live=str(int(self._ipay_live)),
                                auto=str(int(self._autopay)),
                                txnid=values['reference'],
                                productinfo=values['reference'],
                                amount=values['amount'],
                                phone=phone,
                                email=values.get('partner_email'),
                                service_provider=self._ipay_vendor_id,
                                currency_code='KES',
                                surl=urls.url_join(base_url, '/payment/ipay/ipn'),
                                cst='1',
                                crl='0',
                                bonga='1',
                                vooma='1',
                                channel='Odoo',
                                )

        text = "{0}{1}{2}{3}{4}{5}{6}{7}{8}{9}{10}".format( ipay_values['live'],
                                                    ipay_values['txnid'],
                                                    ipay_values['productinfo'],
                                                    ipay_values['amount'],
                                                    ipay_values['phone'],
                                                    ipay_values['email'],
                                                    ipay_values['service_provider'],
                                                    ipay_values['currency_code'],
                                                    ipay_values['surl'],
                                                    ipay_values['cst'],
                                                    ipay_values['crl'])
        hashobj = hmac.new(key1.encode(), text.encode(), hashlib.sha1)
        hashtxt = hashobj.hexdigest()
        ipay_values.update({
            'hash': hashtxt,
        })
        return ipay_values

    def ipay_get_form_action_url(self):
        self.ensure_one()
        environment = "prod" if self._ipay_live else "test"
        return self._get_ipay_urls(environment)


class PaymentTransactionIpayOdoo(models.Model):
    _inherit = 'payment.transaction'

    def _ipay_form_validate(self,data):
        # try and search for a non-empty vid field in the payment 
        # acquirer model.
        ipay_data = self.env['payment.acquirer'].sudo().search([('_ipay_vendor_id', '!=', '')], limit=1)
        live = ipay_data._ipay_live
        vid  = ipay_data._ipay_vendor_id

        # unpack ipn data
        val1 = data.get('id') 
        val2 = data.get('ivm') 
        val3 = data.get('qwh') 
        val4 = data.get('afd') 
        val5 = data.get('poi') 
        val6 = data.get('uyt') 
        val7 = data.get('ifd')
        txn  = data.get('txncd')
        ipn_url = "{0}{1}{2}{3}{4}{5}{6}{7}{8}{9}{10}{11}{12}{13}{14}".format( 'https://www.ipayafrica.com/ipn/?vendor=', vid,
                                                                    '&id=',val1,'&ivm=',val2,'&qwh=',val3,'&afd=',val4,'&poi=',val5,'&uyt=',val6,'ifd=',val7)
        r = requests.get(ipn_url)
        if live:
            code = data.get('status')
            _logger.info("iPay IPN return info: %s for tx: %s", str(code), str(val1))
            # successful, more and already paid
            if code == 'aei7p7yrx4ae34' or code == 'eq3i7p5yt7645e' or code == 'cr5i3pgy9867e1':
                _logger.info("iPay payment processed for: %s", str(txn))
                self.write({'acquirer_reference': txn})
                self._set_transaction_done()
                return True
            # pending
            if code == 'bdi6p2yy76etrs':
                _logger.info("iPay payment pending for: %s", str(txn))
                self.write({'acquirer_reference': txn})
                self._set_transaction_pending()
                return True
            # failed or less
            if code == 'fe2707etr5s4wq' or code == 'dtfi4p7yty45wq':
                _logger.info("iPay payment failed/ less for: %s", str(txn))
                self.write({'acquirer_reference': txn})
                self._set_transaction_cancel()
                return True
            return False
        else:
            code = r.content
            _logger.info("iPay IPN return info: %s for tx: %s", str(code), str(val1))
            _logger.info("iPay tested payment code: %s", str(txn))
            self.write({'acquirer_reference': txn})
            self._set_transaction_done()
            return True
