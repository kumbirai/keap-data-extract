"""Update note_type enum

Revision ID: update_note_type_enum
Revises: 
Create Date: 2024-03-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'update_note_type_enum'
down_revision = None
branch_labels = None
depends_on = None

# Define the new enum values
new_note_types = [
    'Call', 'Email', 'Fax', 'Letter', 'Meeting', 'Other', 'Task', 'SMS', 'Social',
    'Chat', 'Voicemail', 'Website', 'Form', 'Appointment', 'Campaign', 'Contact',
    'Deal', 'Document', 'File', 'Follow Up', 'Invoice', 'Order', 'Product',
    'Purchase', 'Recurring Order', 'Referral', 'Refund', 'Subscription', 'Survey',
    'Tag', 'Template', 'Transaction', 'User', 'Webform', 'Workflow'
]

def upgrade():
    # Check if the enum type exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    enum_exists = False
    for enum in inspector.get_enums():
        if enum['name'] == 'note_type':
            enum_exists = True
            break

    if enum_exists:
        # Create a temporary enum type with the new values
        op.execute("CREATE TYPE note_type_new AS ENUM (" + 
                   ", ".join(f"'{t}'" for t in new_note_types) + ")")
        
        # Update the column to use the new enum type
        op.execute("""
            ALTER TABLE notes 
            ALTER COLUMN type TYPE note_type_new 
            USING type::text::note_type_new
        """)
        
        # Drop the old enum type
        op.execute("DROP TYPE note_type")
        
        # Rename the new enum type to the original name
        op.execute("ALTER TYPE note_type_new RENAME TO note_type")
    else:
        # Create the enum type directly
        op.execute("CREATE TYPE note_type AS ENUM (" + 
                   ", ".join(f"'{t}'" for t in new_note_types) + ")")

def downgrade():
    # Define the old enum values
    old_note_types = [
        'Call', 'Email', 'Fax', 'Letter', 'Meeting', 'Other', 'Task', 'SMS', 'Social',
        'Chat', 'Voicemail', 'Website', 'Form'
    ]
    
    # Check if the enum type exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    enum_exists = False
    for enum in inspector.get_enums():
        if enum['name'] == 'note_type':
            enum_exists = True
            break

    if enum_exists:
        # Create a temporary enum type with the old values
        op.execute("CREATE TYPE note_type_old AS ENUM (" + 
                   ", ".join(f"'{t}'" for t in old_note_types) + ")")
        
        # Update the column to use the old enum type
        # Note: This will fail if there are any notes using the new enum values
        op.execute("""
            ALTER TABLE notes 
            ALTER COLUMN type TYPE note_type_old 
            USING type::text::note_type_old
        """)
        
        # Drop the new enum type
        op.execute("DROP TYPE note_type")
        
        # Rename the old enum type to the original name
        op.execute("ALTER TYPE note_type_old RENAME TO note_type")
    else:
        # Create the enum type directly with old values
        op.execute("CREATE TYPE note_type AS ENUM (" + 
                   ", ".join(f"'{t}'" for t in old_note_types) + ")") 