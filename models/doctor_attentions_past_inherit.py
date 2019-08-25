# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)
import openerp
import re
import codecs
from openerp.osv import fields, osv
from openerp.tools.translate import _

class doctor_attentions_past(osv.osv):
    _name = "doctor.attentions.past"
    _inherit = "doctor.attentions.past"
    
    _columns = {
        'attentiont_pediatrics_id': fields.many2one('doctor.attentions.pediatrics', 'Pediatric Attention'),
    }


doctor_attentions_past()