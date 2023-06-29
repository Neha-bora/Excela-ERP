import frappe
from frappe.utils import validate_email_address

@frappe.whitelist(allow_guest=True)
def signup(email, pwd, full_name, user_category, phone , country):
    if validate_email_address(email):
        try:
            user_name=full_name.split(" ")
            user_doc = frappe.get_doc({'doctype':'User',"first_name":user_name[0] if user_name else "",
        "last_name":user_name[1] if len(user_name)>=2 else "", "email":email, "user_category":user_category,
                  "username":email,"send_welcome_email":0,"new_password":pwd, "phone":phone , "location": country,
                  'roles':[{'role':'Customer'}]})
            user_doc.insert(ignore_permissions=True)
            customer_doc=frappe.get_doc({'doctype':'Customer',"first_name":user_doc.first_name,
                                "last_name":user_doc.last_name,"customer_name":user_doc.full_name,
                                "email_id1":user_doc.email,"customer_group":"Individual",
                                "territory":"All Territories"
                                })
            customer_doc.insert(ignore_permissions=True)
            # share_document(doctype="Customer",document=customer_doc.name,user=user_doc.name)
            frappe.get_doc({'doctype':'User Permission','user':user_doc.name,
                                        'allow':'Customer','for_value':customer_doc.name,'is_default':1,
                                        'apply_to_all_doctypes':1}).insert(ignore_permissions=True)
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
        "first_name":user.first_name,
        "middle_name" : user.middle_name,
        "last_name" : user.last_name,
        "full_name": user.full_name,
        "user_category":user.user_category
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
        job_listing_table= frappe.qb.DocType("Job Opening")
        job_listing = (
            frappe.qb.from_(job_listing_table)
            .select(
                job_listing_table.job_title , 
                job_listing_table.designation , 
                job_listing_table.department , 
                job_listing_table.description , 
                job_listing_table.vacancies , 
                job_listing_table.status
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
                res['job_listing']= job_listing
                return res
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), e)