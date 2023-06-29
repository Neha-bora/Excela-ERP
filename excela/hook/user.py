import frappe

def validate(doc):
    # if doc.is_new():
    create_customer(doc)

def create_customer(doc):
    frappe.msgprint("validate trigger")
        # doc = {
        #     "customer_name": doc.name,
        #     "customer_group": "Commercial",
        #     "territory": "All Territories",
        # }
        # customer = frappe.new_doc("Customer")
        # customer.flags.ignore_mandatory = True
        # customer.update(doc)
        # customer.save()