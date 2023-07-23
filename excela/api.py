import json
import frappe
from frappe.utils import validate_email_address
import base64

@frappe.whitelist(allow_guest=True)
def signup(email, pwd, full_name, user_category, phone, country, country_code):
    if validate_email_address(email):
        try:
            user_name = full_name.split(" ")
            user_doc = frappe.get_doc({'doctype': 'User', "first_name": user_name[0] if user_name else "",
                                       "last_name": user_name[1] if len(user_name) >= 2 else "", "email": email, "user_category": user_category,
                                       "username": email, "send_welcome_email": 0, "new_password": pwd, "phone": phone, "location": country,
                                       "country_code": country_code, 'roles': [{'role': 'Customer'}]})
            user_doc.insert(ignore_permissions=True)
            customer_doc = frappe.get_doc({'doctype': 'Customer', 
                                            "first_name": user_doc.first_name,
                                            "last_name": user_doc.last_name, 
                                            "customer_name": user_doc.full_name,
                                            "email_id1": user_doc.email, 
                                            "customer_group": "Individual",
                                            "territory": "All Territories",
                                            "is_agent":1 if user_doc.user_category == "Agent" else 0,
                                            "is_job_seeker": 1 if user_doc.user_category == "Job Seeker" else 0,
                                            "is_student":1 if user_doc.user_category== "Student" else 0,
                                            "is_client_company":1 if user_doc.user_category=="Client Company" else 0
                                           })
            customer_doc.insert(ignore_permissions=True)
            # share_document(doctype="Customer",document=customer_doc.name,user=user_doc.name)
            frappe.get_doc({'doctype': 'User Permission', 'user': user_doc.name,
                            'allow': 'Customer', 'for_value': customer_doc.name, 'is_default': 1,
                            'apply_to_all_doctypes': 1}).insert(ignore_permissions=True)
            login(email, pwd)
        except Exception as e:
            frappe.response["message"] = {
                "success_key": 0,
                "message": e
            }


@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    try:
        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(user=usr, pwd=pwd)
        login_manager.post_login()
    except frappe.exceptions.AuthenticationError:
        frappe.clear_messages()
        frappe.local.response["message"] = {
            "success_key": 0,
            "message": "Incorrect Username or Password"
        }
        return

    if not frappe.db.get_value('User', usr, 'api_key'):
        generate_keys(frappe.session.user)

    user = frappe.get_doc('User', usr)

    frappe.response["message"] = {
        "success_key": 1,
        "message": "success",
        "sid": frappe.session.sid,
        "api_key": user.api_key,
        "api_secret": user.get_password('api_secret'),
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "middle_name": user.middle_name,
        "last_name": user.last_name,
        "full_name": user.full_name,
        "user_category": user.user_category,
        "phone": user.phone,
        "location": user.location,
        "country_code": user.country_code
    }


def generate_keys(user):
    user_details = frappe.get_doc('User', user)
    print(user_details.api_key)
    print(user_details.api_secret)
    api_secret = frappe.generate_hash(length=15)

    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key

    user_details.api_secret = api_secret
    user_details.flags.Ign
    user_details.save(ignore_permissions=True)
    frappe.db.commit()
    return user_details.api_secret, user_details.api_key


@frappe.whitelist(allow_guest=True)
def get_job_listing():
    try:
        res = frappe._dict()
        job_listing_table = frappe.qb.DocType("Job Opening")
        job_listing = (
            frappe.qb.from_(job_listing_table)
            .select(
                job_listing_table.name,
                job_listing_table.job_title,
                job_listing_table.designation,
                job_listing_table.department,
                job_listing_table.description,
                job_listing_table.status,
                job_listing_table.employment_type,
                job_listing_table.job_sector,
                job_listing_table.number_of_vacancies,
                job_listing_table.years_of_experience,
                job_listing_table.lower_range,
                job_listing_table.upper_range
            )
            .where(
                job_listing_table.status == "Open"
            )
        ).run(as_dict=1)
        if job_listing:
            res['success_key'] = 1
            res['message'] = "success"
            res['job_listing'] = job_listing
            return res
        else:
            res["success_key"] = 0
            res["message"] = "No Job list in DB"
            res['job_listing'] = job_listing
            return res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), e)


@frappe.whitelist(allow_guest=True)
def create_job_applicant(applicant_name={}):
    try:
        res = frappe._dict()

        job_applicant = frappe.new_doc("Job Applicant")
        job_applicant.job_title = applicant_name.get("job_id")
        job_applicant.applicant_name = applicant_name.get("applicant_name")
        job_applicant.email_id = applicant_name.get('email_id')
        job_applicant.phone_number = applicant_name.get("phone_number")
        job_applicant.country = applicant_name.get("country")
        job_applicant.cover_letter = applicant_name.get("message")
        job_applicant.passport_no = applicant_name.get("passport_no")
        job_applicant.insert(ignore_permissions=True)

        if applicant_name.get('documents'):
            for attach in applicant_name.get('documents'):
                frappe.get_doc(
                    {
                        "doctype": "File",
                                   "attached_to_doctype": 'Job Applicant',
                                   "attached_to_name": job_applicant.name,
                                   "file_name": attach.get('f_name'),
                                   "is_private": 0,
                                   "content": base64.b64decode(attach.get('f_data').split(',')[1]),
                    }).insert(ignore_permissions=True)

        res['message'] = "success"
        res["job_applicant"] = {
            "name": job_applicant.name,
            "status": job_applicant.status
        }
        return res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), e)
        res['message'] = "failed"


@frappe.whitelist(allow_guest=True)
def job_search(job_title=None, job_type=None, category=None):
    res = frappe._dict()
    conditions = ""
    if job_title:
        conditions+= f' and job_title like "%{job_title}%" '
    if job_type:
        conditions+= f' and employment_type like "%{job_type}%" '
    if category:
        conditions+= f' and job_sector like "%{category}%" '

    job_opening = frappe.db.sql("""Select name,job_title , 
            designation ,department , description ,
            status , employment_type , job_sector ,
            number_of_vacancies , years_of_experience , 
            lower_range , upper_range
        from `tabJob Opening` 
        WHERE 1=1 {0}
        """.format(conditions) , as_dict=1)

    if job_opening:
        res['success_key'] = 1
        res['message'] = "success"
        res['job_opening'] = job_opening
        return res
    else:
        res["success_key"] = 0
        res["message"] = "No Job Opening found"
        res['job_opening'] = job_opening
        return res

@frappe.whitelist(allow_guest=True)
def get_job_details_by_id(job_id):
    try:
        res = frappe._dict()
        job_listing_table = frappe.qb.DocType("Job Opening")
        job_listing = (
            frappe.qb.from_(job_listing_table)
            .select(
                job_listing_table.name,
                job_listing_table.job_title,
                job_listing_table.designation,
                job_listing_table.department,
                job_listing_table.description,
                job_listing_table.status,
                job_listing_table.employment_type,
                job_listing_table.job_sector,
                job_listing_table.number_of_vacancies,
                job_listing_table.years_of_experience,
                job_listing_table.lower_range,
                job_listing_table.upper_range
            )
            .where((job_listing_table.status == "Open") & (job_listing_table.name == job_id)
                   )
        ).run(as_dict=1)
        if job_listing:
            res['success_key'] = 1
            res['message'] = "success"
            res['job_listing'] = job_listing
            return res
        else:
            res["success_key"] = 0
            res["message"] = "No Job list with this name"
            res['job_listing'] = job_listing
            return res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), e)


@frappe.whitelist()
def get_apply_job_by_userid(userid):
    try:
        res = frappe._dict()
        applied_job = frappe.db.sql(''' 
            select
                ja.name , ja.email_id ,ja.applicant_name , ja.status , 
                ja.phone_number,ja.passport_no,
                ja.candidate_status , ja.creation  , ja.cover_letter
            from `tabJob Applicant` ja
            where ja.email_id = %s
        ''', (userid) , as_dict=True)
        for job in applied_job:
            job_details = frappe.db.sql(''' 
            select
                jo.name as job_id , jo.job_title,  
                jo.designation , jo.department ,jo.description, jo.status , 
                jo.employment_type,jo.job_sector , jo.number_of_vacancies ,
                jo.years_of_experience , jo.lower_range, jo.upper_range
            from `tabJob Applicant` ja , `tabJob Opening` jo
            where jo.name = ja.job_title and ja.email_id = %s
            ''',(userid) ,as_dict=True )
            job['job_detail'] = job_details

        if applied_job:
            res['success_key'] = 1
            res['message'] = "success"
            res['applied_job'] = applied_job
            return res
        else:
            res["success_key"] = 0
            res["message"] = "No Job list with this name"
            res['applied_job'] = applied_job
            return res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), e)

# @frappe.whitelist(allow_guest=True)
# def get_user_profile():
#     res = frappe._dict()
#     user = frappe.db.sql(''' 
#             select
#                 email , first_name , last_name , full_name , 
#                 username , phone, location, country_code , user_category
#             from `tabUser`
#     ''' , as_dict=True)

#     for job in user:
#         applied_job = frappe.db.sql(''' 
#         select ja.job_title from `tabJob Applicant` ja , `tabUser` u
#         where ja.email_id = u.email
#         ''' , as_dict=True)
#         job['applied_job'] = applied_job
#     if user:
#         res["success_key"] = 1
#         res["message"] = "success"
#         res['user_details'] = user
#         return res
#     else:
#         res["success_key"] = 0
#         res["message"] = "No user found"
#         res['user_details'] = user
#         return res