# -*- coding: utf-8 -*-
import logging
from openerp.osv import osv, fields
from datetime import datetime, timedelta, date
from dateutil import relativedelta as rdelta
from openerp.tools.translate import _
import urllib
import urllib2
from dateutil.relativedelta import relativedelta
from unicodedata import normalize
import string

_logger = logging.getLogger(__name__)


class doctor_attentions_pediatrics(osv.Model):
    _name = 'doctor.attentions.pediatrics'
    _rec_name = 'number'
    _order = "date_attention desc"

    #Niveles de estudio
    educational_level = [
        ('5', 'JARDIN'),
        ('6', 'PRIMARIA'),
        ('7', 'SECUNDARIA'),
        ('1', 'PREGRADO'),
        ('2', 'POSGRADO'),
        ('3', u'MAESTRÍAS'),
        ('4', u'ESPECIALIZACIÓN'),
    ]


    def create(self, cr, uid, vals, context=None):
        # Set appointment number if empty
        if not vals.get('number'):
            vals['number'] = self.pool.get('ir.sequence').get(cr, uid, 'attention.sequence')
        return super(doctor_attentions_pediatrics, self).create(cr, uid, vals, context=context)

    def button_closed(self, cr, uid, ids, context=None):
        ids_attention_past = self.pool.get('doctor.attentions.past').search(cr, uid, [('attentiont_id', '=', ids),
                                                                                      ('past', '=', False)],
                                                                            context=context)
        self.pool.get('doctor.attentions.past').unlink(cr, uid, ids_attention_past, context)

        ids_review_system = self.pool.get('doctor.review.systems').search(cr, uid, [('attentiont_id', '=', ids),
                                                                                    ('review_systems', '=', False)],
                                                                          context=context)
        self.pool.get('doctor.review.systems').unlink(cr, uid, ids_review_system, context)

        ids_examen_fisico = self.pool.get('doctor.attentions.exam').search(cr, uid, [('attentiont_id', '=', ids),
                                                                                     ('exam', '=', False)],
                                                                           context=context)
        self.pool.get('doctor.attentions.exam').unlink(cr, uid, ids_examen_fisico, context)
        return super(doctor_attentions_pediatrics, self).write(cr, uid, ids, {'state': 'closed'}, context=context)

    def _previous(self, cr, uid, patient_id, type_past, attentiont_id=None):
        condition = [('patient_id', '=', patient_id.id)]
        if attentiont_id != None:
            condition.append(('attentiont_id', '<=', attentiont_id))
        if type_past == 'past':
            return self.pool.get('doctor.attentions.past').search(cr, uid, condition, order='id desc')
        if type_past == 'pathological':
            return self.pool.get('doctor.diseases.past').search(cr, uid, condition, order='id desc')
        if type_past == 'drugs':
            return self.pool.get('doctor.atc.past').search(cr, uid, condition, order='id desc')

    def _get_past(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for datos in self.browse(cr, uid, ids):
            res[datos.id] = self._previous(cr, uid, datos.patient_id, 'past', datos.id)
        return res

    def _get_pathological_past(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for datos in self.browse(cr, uid, ids):
            res[datos.id] = self._previous(cr, uid, datos.patient_id, 'pathological', datos.id)
        return res

    def _get_drugs_past(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for datos in self.browse(cr, uid, ids):
            res[datos.id] = self._previous(cr, uid, datos.patient_id, 'drugs', datos.id)
        return res

    _columns = {
        'patient_id': fields.many2one('doctor.patient', 'Patient', ondelete='restrict', readonly=True),
        'patient_photo': fields.related('patient_id', 'photo', type="binary", relation="doctor.patient", readonly=True),
        'date_attention': fields.datetime('Fecha Atención', required=True, readonly=True),
        'number': fields.char('Número Atención', select=1, size=32, readonly=True,
                              help="Número Antención. Esta secuencia será calculada automaticamente al guardar."),
        'origin': fields.char('Origen', size=64,
                              help="Reference of the document that produced this attentiont.", readonly=True),
        'age_attention': fields.integer('Current age', readonly=True),
        'age_unit': fields.selection([('1', 'Years'), ('2', 'Months'), ('3', 'Days'), ], 'Unit of measure of age',
                                     readonly=True),
        'age_patient_ymd': fields.char('Age in Years, months and days', size=30, readonly=True),

        'professional_id': fields.many2one('doctor.professional', 'Doctor', required=True, readonly=True),
        'speciality': fields.related('professional_id', 'speciality_id', type="many2one", relation="doctor.speciality",
                                     string='Speciality', required=False, store=True,
                                     states={'closed': [('readonly', True)]}),
        'professional_photo': fields.related('professional_id', 'photo', type="binary", relation="doctor.professional",
                                             readonly=True, store=False),
        'actual_disease': fields.text('Actual Disease', required=False, states={'closed': [('readonly', True)]}),
        'reason_consultation' : fields.char("Reason of Consultation", size=100, required=False, states={'closed': [('readonly', True)]}),
        'review_systems_id': fields.one2many('doctor.review.systems', 'attentiont_pediatrics_id', 'Review of systems',
                                             ondelete='restrict', states={'closed': [('readonly', True)]}),
        'attentions_past_ids': fields.one2many('doctor.attentions.past', 'attentiont_id', 'Past', ondelete='restrict',
                                               states={'closed': [('readonly', True)]}),
        'past_ids': fields.function(_get_past, relation="doctor.attentions.past", type="one2many", store=False,
                                    readonly=True, method=True, string="Old Past"),
        'pathological_past': fields.one2many('doctor.diseases.past', 'attentiont_id', 'Pathological past',
                                             ondelete='restrict', states={'closed': [('readonly', True)]}),
        'pathological_past_ids': fields.function(_get_pathological_past, relation="doctor.diseases.past",
                                                 type="one2many", store=False, readonly=True, method=True,
                                                 string="Old Pathological Past"),
        'drugs_past': fields.one2many('doctor.atc.past', 'attentiont_id', 'Drugs past', ondelete='restrict',
                                      states={'closed': [('readonly', True)]}),
        'drugs_past_ids': fields.function(_get_drugs_past, relation="doctor.atc.past", type="one2many", store=False,
                                          readonly=True, method=True, string="Old drugs Past"),
        'body_mass_index': fields.float('Body Mass Index', states={'closed': [('readonly', True)]}),
        'heart_rate': fields.integer('Heart Rate', help="Heart rate expressed in beats per minute",
                                     states={'closed': [('readonly', True)]}),
        'respiratory_rate': fields.integer('Respiratory Rate', help="Respiratory rate expressed in breaths per minute",
                                           states={'closed': [('readonly', True)]}),
        'temperature': fields.float('Temperature (celsius)', states={'closed': [('readonly', True)]}),
        'arterial_tension': fields.integer('TA', help="Arterial Tension",
                                        states={'closed': [('readonly', True)]}),
        'attentions_exam_ids': fields.one2many('doctor.attentions.exam', 'attentiont_pediatrics_id', 'Exam', ondelete='restrict',
                                               states={'closed': [('readonly', True)]}),
        'analysis': fields.text('Analysis', required=False, states={'closed': [('readonly', True)]}),
        'conduct': fields.text('Conduct', required=False, states={'closed': [('readonly', True)]}),
        'diseases_ids': fields.one2many('doctor.attentions.diseases', 'attentiont_id', 'Diseases', ondelete='restrict',
                                        states={'closed': [('readonly', True)]}),
        'drugs_ids': fields.one2many('doctor.prescription', 'attentiont_id', 'Drugs prescription', ondelete='restrict',
                                     states={'closed': [('readonly', True)]}),
        'diagnostic_images_ids': fields.one2many('doctor.attentions.procedures', 'attentiont_id', 'Diagnostic Images',
                                                 ondelete='restrict', states={'closed': [('readonly', True)]},
                                                 domain=[('procedures_id.procedure_type', '=', 3)]),
        'clinical_laboratory_ids': fields.one2many('doctor.attentions.procedures', 'attentiont_id',
                                                   'Clinical Laboratory', ondelete='restrict',
                                                   states={'closed': [('readonly', True)]},
                                                   domain=[('procedures_id.procedure_type', '=', 4)]),
        'surgical_procedure_ids': fields.one2many('doctor.attentions.procedures', 'attentiont_id', 'Surgical Procedure',
                                                  ondelete='restrict', states={'closed': [('readonly', True)]},
                                                  domain=[('procedures_id.procedure_type', '=', 2)]),
        'therapeutic_procedure_ids': fields.one2many('doctor.attentions.procedures', 'attentiont_id',
                                                     'Therapeutic Procedure', ondelete='restrict',
                                                     states={'closed': [('readonly', True)]},
                                                     domain=[('procedures_id.procedure_type', '=', 5)]),
        'other_procedure_ids': fields.one2many('doctor.attentions.procedures', 'attentiont_id', 'Other Procedure',
                                               ondelete='restrict', states={'closed': [('readonly', True)]},
                                               domain=['|', ('procedures_id.procedure_type', '=', 1), '|',
                                                       ('procedures_id.procedure_type', '=', 6),
                                                       ('procedures_id.procedure_type', '=', 7)]),
        'referral_ids': fields.one2many('doctor.attentions.referral', 'attentiont_id', 'Referral', ondelete='restrict',
                                        states={'closed': [('readonly', True)]}),
        'disability_ids': fields.one2many('doctor.attentions.disability', 'attentiont_id', 'Disability',
                                          ondelete='restrict', states={'closed': [('readonly', True)]}),
        'state': fields.selection([('open', 'Open'), ('closed', 'Closed')], 'Status', readonly=True, required=True),
        'tipo_historia': fields.char('tipo_historia', required=True),

        'patient_sex' : fields.selection([('m', 'Male'), ('f', 'Female'), ], 'Sex', select=True),
        'patient_educational_level': fields.selection(educational_level, 'Educational Level', required=False),
        'patient_beliefs' : fields.char('Beliefs'),
        'patient_birth_date': fields.date('Date of Birth'),

        'father_name' : fields.char('Father Name', size=30),
        'father_age' : fields.integer('Father Age'),
        'mother_name' : fields.char('Mother Name', size=30),
        'mother_age' : fields.integer('Mother Age'),

        #familiar antecedents
        'antfam_healthy_mother': fields.boolean('Healthy Mother'),
        'antfam_dead_mother':   fields.boolean('Dead Mother'),
        'antfam_mother_disease' : fields.char('Mother Disease'),

        'antfam_healthy_father': fields.boolean('Healthy Father'),
        'antfam_dead_father':   fields.boolean('Dead Father'),
        'antfam_father_disease' : fields.char('Father Disease'),

        'antfam_sibling_age' : fields.integer('Sibling age'),
        'antfam_healthy_sibling': fields.boolean('Healthy Sibling'),
        'antfam_dead_sibling':   fields.boolean('Dead Sibling'),
        'antfam_sibling_disease' : fields.char('Sibling Disease'),

        'antfam_sibling2_age' : fields.integer('Sibling age'),
        'antfam_healthy_sibling2': fields.boolean('Healthy Sibling'),
        'antfam_dead_sibling2':   fields.boolean('Dead Sibling'),
        'antfam_sibling2_disease' : fields.char('Sibling Disease'),

        'antfam_sibling3_age' : fields.integer('Sibling age'),
        'antfam_healthy_sibling3': fields.boolean('Healthy Sibling'),
        'antfam_dead_sibling3':   fields.boolean('Dead Sibling'),
        'antfam_sibling3_disease' : fields.char('Sibling Disease'),

        'antfam_healthy_maternalgrandma': fields.boolean('Healthy Maternal Grandma'),
        'antfam_dead_maternalgrandma':   fields.boolean('Dead Maternal Grandma'),
        'antfam_maternalgrandma_disease' : fields.char('Maternal Grandma Disease'),

        'antfam_healthy_maternalgrandpa': fields.boolean('Healthy Maternal Grandpa'),
        'antfam_dead_maternalgrandpa':   fields.boolean('Dead Maternal Grandpa'),
        'antfam_maternalgrandpa_disease' : fields.char('Maternal Grandpa Disease'),

        'antfam_healthy_paternalgrandma': fields.boolean('Healthy Paternal Grandma'),
        'antfam_dead_paternalgrandma':   fields.boolean('Dead Paternal Grandma'),
        'antfam_paternalgrandma_disease' : fields.char('Paternal Grandma Disease'),

        'antfam_healthy_other': fields.boolean('Healthy Other'),
        'antfam_dead_other':   fields.boolean('Dead Other'),
        'antfam_other_disease' : fields.char('Other Disease'),

        'antfam_smoke' : fields.boolean('Someone smoke at home?'),
        'antfam_smoke_who': fields.char('Who', size=50),

    }

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        rec_name = 'number'
        res = [(r['id'], r[rec_name])
               for r in self.read(cr, uid, ids, [rec_name], context)]
        return res

    def onchange_professional(self, cr, uid, ids, professional_id, context=None):
        values = {}
        if not professional_id:
            return values
        professional_data = self.pool.get('doctor.professional').browse(cr, uid, professional_id, context=context)
        professional_img = professional_data.photo
        if professional_data.speciality_id.id:
            professional_speciality = professional_data.speciality_id.id
            values.update({
                'speciality': professional_speciality,
            })

        values.update({
            'professional_photo': professional_img,
        })
        _logger.info(values)
        return {'value': values}

    def onchange_patient(self, cr, uid, ids, patient_id, context=None):
        values = {}
        if not patient_id:
            return values
        past = self.pool.get('doctor.attentions.past').search(cr, uid, [('patient_id', '=', patient_id)],
                                                              order='id asc')
        phatological_past = self.pool.get('doctor.diseases.past').search(cr, uid, [('patient_id', '=', patient_id)],
                                                                         order='id asc')
        drugs_past = self.pool.get('doctor.atc.past').search(cr, uid, [('patient_id', '=', patient_id)], order='id asc')
        patient_data = self.pool.get('doctor.patient').browse(cr, uid, patient_id, context=context)
        photo_patient = patient_data.photo

        values.update({
            'patient_photo': photo_patient,
            'past_ids': past,
            'pathological_past_ids': phatological_past,
            'drugs_past_ids': drugs_past,
        })
        return {'value': values}

    def calcular_edad(self, fecha_nacimiento):
        current_date = datetime.today()
        st_birth_date = datetime.strptime(fecha_nacimiento, '%Y-%m-%d')
        re = current_date - st_birth_date
        dif_days = re.days
        age = dif_days
        age_unit = ''
        if age < 30:
            age_attention = age,
            age_unit = '3'

        elif age > 30 and age < 365:
            age = age / 30
            age = int(age)
            age_attention = age,
            age_unit = '2'

        elif age >= 365:
            age = int((current_date.year - st_birth_date.year - 1) + (
                1 if (current_date.month, current_date.day) >= (st_birth_date.month, st_birth_date.day) else 0))
            age_attention = age,
            age_unit = '1'

        return age

    # it allows to return the patient's age in years, months, days e.g  24 years, 8 months, 3 days. -C
    def calcular_edad_ymd(self, fecha_nacimiento):
        today = date.today()
        age = relativedelta(today, datetime.strptime(fecha_nacimiento, '%Y-%m-%d'))
        age_ymd = str(age.years) + ' Años, ' + str(age.months) + ' Meses,' + str(age.days) + ' Días'
        return age_ymd

    def calcular_age_unit(self, fecha_nacimiento):
        current_date = datetime.today()
        st_birth_date = datetime.strptime(fecha_nacimiento, '%Y-%m-%d')
        re = current_date - st_birth_date
        dif_days = re.days
        age = dif_days
        age_unit = ''
        if age < 30:
            age_unit = '3'
        elif age > 30 and age < 365:
            age_unit = '2'

        elif age >= 365:
            age_unit = '1'

        return age_unit

    def _get_professional_id(self, cr, uid, user_id):
        try:
            professional_id = self.pool.get('doctor.professional').browse(cr, uid,
                                                                          self.pool.get('doctor.professional').search(
                                                                              cr, uid, [('user_id', '=', uid)]))[0].id
            return professional_id
        except:
            return False

    def default_get(self, cr, uid, fields, context=None):
        res = super(doctor_attentions_pediatrics, self).default_get(cr, uid, fields, context=context)

        modelo_permisos = self.pool.get('res.groups')
        nombre_permisos = []
        cr.execute("SELECT gid FROM res_groups_users_rel WHERE uid = %s" % (uid))

        for i in cr.fetchall():
            grupo_id = modelo_permisos.browse(cr, uid, i[0], context=context).name
            nombre_permisos.append(grupo_id)

        if context.get('active_model') == "doctor.patient":
            id_paciente = context.get('default_patient_id')
        else:
            id_paciente = context.get('patient_id')

        registros_categorias = []
        registros_examenes_fisicos = []
        
        ids = self.pool.get('doctor.systems.category').search(cr,uid,[('active','=',True)],context=context)
        
        for i in self.pool.get('doctor.systems.category').browse(cr,uid,ids,context=context):
            registros_categorias.append((0,0,{'system_category' : i.id,}))
            #pre-loading systems for the attention

        _logger.info("====> ids = %s" % registros_categorias)
        
        ids_examenes_fisicos = self.pool.get('doctor.exam.category').search(cr,uid,[('active','=',True)],context=context)
        for i in self.pool.get('doctor.exam.category').browse(cr,uid,ids_examenes_fisicos,context=context):
            registros_examenes_fisicos.append((0,0,{'exam_category' : i.id}))
        #pre-loading exams for the attention
       

        if id_paciente:
            fecha_nacimiento = self.pool.get('doctor.patient').browse(cr, uid, id_paciente, context=context).birth_date
            res['age_patient_ymd'] = self.calcular_edad_ymd(fecha_nacimiento)
            res['age_attention'] = self.calcular_edad(fecha_nacimiento)
            res['age_unit'] = self.calcular_age_unit(fecha_nacimiento)
            res['review_systems_id'] = registros_categorias
            res['attentions_exam_ids'] = registros_examenes_fisicos

        return res

    _defaults = {
        'patient_id': lambda self, cr, uid, context: context.get('patient_id', False),
        'date_attention': lambda *a: datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S"),
        'professional_id': _get_professional_id if _get_professional_id != False else False,
        'state': 'open',
        'tipo_historia': 'hc_pediatrics'
    }


doctor_attentions_pediatrics()
