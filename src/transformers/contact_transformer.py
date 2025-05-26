from datetime import datetime

from sqlalchemy.orm import Session

from src.models.models import (Address, Contact, ContactCustomFieldValue, EmailAddress, FaxNumber, Note, Opportunity, Order, PhoneNumber, Subscription, Tag, Task)


class ContactTransformer:
    @staticmethod
    def transform(data: dict, db: Session) -> Contact:
        """Transform contact data from Keap API to database model."""
        # Create or update contact
        contact = db.query(Contact).filter_by(id=data['id']).first()
        if not contact:
            contact = Contact(id=data['id'])
            db.add(contact)

        # Update basic fields
        contact.given_name = data.get('given_name')
        contact.family_name = data.get('family_name')
        contact.email = data.get('email_address')
        contact.company_name = data.get('company_name')
        contact.job_title = data.get('job_title')
        contact.website = data.get('website')
        contact.anniversary = data.get('anniversary')
        contact.birthday = data.get('birthday')
        contact.background = data.get('background')
        contact.last_updated = datetime.utcnow()

        # Handle addresses
        if 'addresses' in data:
            # Clear existing address relationships
            contact.addresses = []
            for addr_data in data['addresses']:
                address = Address(id=addr_data[
                    'id'], line1=addr_data.get('line1'), line2=addr_data.get('line2'), city=addr_data.get('city'), state=addr_data.get('state'), postal_code=addr_data.get('postal_code'),
                                  country=addr_data.get('country'), type=addr_data.get('type'))
                db.add(address)
                contact.addresses.append(address)

        # Handle email addresses
        if 'email_addresses' in data:
            # Clear existing email relationships
            contact.email_addresses = []
            for email_data in data['email_addresses']:
                email = EmailAddress(id=email_data['id'], email=email_data.get('email'), field=email_data.get('field'))
                db.add(email)
                contact.email_addresses.append(email)

        # Handle phone numbers
        if 'phone_numbers' in data:
            # Clear existing phone relationships
            contact.phone_numbers = []
            for phone_data in data['phone_numbers']:
                phone = PhoneNumber(id=phone_data['id'], number=phone_data.get('number'), field=phone_data.get('field'))
                db.add(phone)
                contact.phone_numbers.append(phone)

        # Handle fax numbers
        if 'fax_numbers' in data:
            # Clear existing fax relationships
            contact.fax_numbers = []
            for fax_data in data['fax_numbers']:
                fax = FaxNumber(id=fax_data['id'], number=fax_data.get('number'), field=fax_data.get('field'))
                db.add(fax)
                contact.fax_numbers.append(fax)

        # Handle tags
        if 'tags' in data:
            # Clear existing tag relationships
            contact.tags = []
            for tag_data in data['tags']:
                tag = db.query(Tag).filter_by(id=tag_data['id']).first()
                if not tag:
                    tag = Tag(id=tag_data['id'], name=tag_data.get('name'))
                    db.add(tag)
                contact.tags.append(tag)

        # Handle custom field values
        if 'custom_fields' in data:
            # Clear existing custom field values
            contact.custom_field_values = []
            for field_data in data['custom_fields']:
                custom_value = ContactCustomFieldValue(id=field_data['id'], field_id=field_data.get('field_id'), value=field_data.get('value'))
                db.add(custom_value)
                contact.custom_field_values.append(custom_value)

        # Handle opportunities
        if 'opportunities' in data:
            # Clear existing opportunity relationships
            contact.opportunities = []
            for opp_data in data['opportunities']:
                opportunity = Opportunity(id=opp_data['id'], title=opp_data.get('title'), value=opp_data.get('value'), status=opp_data.get('status'))
                db.add(opportunity)
                contact.opportunities.append(opportunity)

        # Handle tasks
        if 'tasks' in data:
            # Clear existing task relationships
            contact.tasks = []
            for task_data in data['tasks']:
                task = Task(id=task_data['id'], title=task_data.get('title'), description=task_data.get('description'), due_date=task_data.get('due_date'), status=task_data.get('status'))
                db.add(task)
                contact.tasks.append(task)

        # Handle notes
        if 'notes' in data:
            # Clear existing note relationships
            contact.notes = []
            for note_data in data['notes']:
                note = Note(id=note_data['id'], title=note_data.get('title'), body=note_data.get('body'), created_at=note_data.get('created_at'))
                db.add(note)
                contact.notes.append(note)

        # Handle orders
        if 'orders' in data:
            # Clear existing order relationships
            contact.orders = []
            for order_data in data['orders']:
                order = Order(id=order_data['id'], order_number=order_data.get('order_number'), order_date=order_data.get('order_date'), total=order_data.get('total'), status=order_data.get('status'))
                db.add(order)
                contact.orders.append(order)

        # Handle subscriptions
        if 'subscriptions' in data:
            # Clear existing subscription relationships
            contact.subscriptions = []
            for sub_data in data['subscriptions']:
                subscription = Subscription(id=sub_data['id'], status=sub_data.get('status'), next_bill_date=sub_data.get('next_bill_date'))
                db.add(subscription)
                contact.subscriptions.append(subscription)

        return contact
