# -*- coding: utf-8 -*-
import logging
_logger = logging.getLogger(__name__)
import openerp
import re
import codecs
from openerp.osv import fields, osv
from openerp.tools.translate import _


class doctor_review_systems_inherit(osv.osv):
	_name = "doctor.review.systems"
	_inherit = "doctor.review.systems"

	_columns = {
		'attentiont_pediatrics_id': fields.many2one('doctor.attentions.pediatrics', 'Attention'),
	}