"""Identity-join documentary rendering, with the same independent hidden oracle.

Directory: target employee maps to account U_K. Event: actor account U_(1-X1).
The event concerns the target exactly when K XOR X1 = 1. This replaces explicit
bit fragments with a small identity-correlation task, without claiming realism
validated by forensic practitioners.
"""
import random


def render_identity(case):
    rng=random.Random(case['seed']+91731)
    names=['Ada Martin','Noah Bernard','Lina Moreau','Eli Laurent','Maya Robert','Leo Simon']
    person=rng.choice(names)
    company=rng.choice(['Northbridge Research','Meridian Labs','Cedar Systems','Orion Engineering'])
    actions=['opened the restricted design archive','copied the confidential archive to USB',
             'sent the restricted archive to an external mailbox','approved a collaborator access request']
    for nid,node in case['nodes'].items():
        record=node.get('record')
        if not record:continue
        style=rng.randrange(4)
        header=f'Organization: {company}. Internal export, 2025-03-{10+rng.randrange(14):02d}. File: {nid}.\n'
        if record['kind']=='noise':
            body=rng.choice([
                'From: facilities@office.example\nSubject: Stationery order\nPlease confirm the quantity of paper and ink for next month. The delivery address is unchanged.',
                'From: events@office.example\nSubject: Team lunch\nThe restaurant booking is for Thursday at noon. Please send dietary preferences before Tuesday.',
                'Quarterly operations note. Office maintenance and room bookings were reviewed. The printer service contract has been renewed.',
                'Supplier invoice summary. The order covers monitors and ergonomic chairs. Accounting will reconcile the purchase order next week.'
            ])
        else:
            h=record['h'];body=f'Question H{h}: did {person} {actions[h]}?\n'
            if record['kind']=='direct':
                phrase='reports that the event occurred for the target employee' if record['bit'] else 'reports that the event did not occur for the target employee'
                body+=f'Record type: witness_statement. The signed review {phrase}.\n'
            elif record['slot']==0:
                body+=f'Record type: identity_directory. Correlation key: {record["pair"]}.\n'
                body+=f'During this investigation interval, employee {person} is mapped to account U{record["bit"]}. The other account belongs to another employee.\n'
            else:
                body+=f'Record type: audit_event. Correlation key: {record["pair"]}.\n'
                body+=f'The event "{actions[h]}" was recorded for account U{1-record["bit"]}. This export alone does not identify the employee.\n'
            body+='Export quality class: S.\n'
            if record.get('target_path'):
                body+='Related export path: '+' > '.join(record['target_path'])+'.\n'
        node['text']=header+body
    case['documentary']={'rendering':'identity_join','fictional':True,'target':person,'organization':company,
                         'quality_class_S':.85,'note':'Controlled identity-correlation scenario; no expert realism validation.'}
