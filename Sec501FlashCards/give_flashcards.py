

def main():
    with open('sec_obj', 'r') as stream:
        my_file = stream.read().split('\n')

    nc = Notecards()
    for line, term in enumerate(my_file):
        if nc.keys_left and nc.keys_left[0].startswith(term):
            nc.next_section()

        if term.startswith('•'):
            term = term.lstrip('• ')
            nc.add_card(term)
            # If next term starts with '-'
            ## Add all sub terms next in list that starts with '-'
            if my_file[line + 1][0] == '-':
                definition_terms = []
                for sub_term in my_file[line + 1:]:
                    if sub_term[0] == '-':
                        definition_terms.append(sub_term)
                    elif sub_term[0] == '•':
                        break
                nc.add_card(term, definition_terms)

        elif term.startswith('-'):
            term = term.lstrip('- ')
            if my_file[line + 1][0] == '-':
                nc.add_card(term)
            # If next term starts with ' -'
            ## Add all sub terms next in list that starts with ' -'
            elif my_file[line + 1][:2] == ' -':
                definition_terms = []
                for sub_term in my_file[line + 1:]:
                    if sub_term[:2] == ' -':
                        definition_terms.append(sub_term)
                    elif sub_term[0] == '-':
                        break
                nc.add_card(term, definition_terms)
        
        elif term.startswith(' -'):
            # Didn't see any good terms to make into
            # single card
            continue
        elif term == 'EOF':
            break
        else:
            print(f'Dirty Value: {term} Line:{line}')

    nc.write_to_csv('comptia_sec_501')


class Notecards:
    def __init__(self):
        self.headers = get_headers()
        self.keys_left = [keyword[0] for keyword in self.headers][1:]
        self.cards = { val.split(':')[0]: [] for key, val in self.headers}

        self._current_section = self.headers.pop(0)


    def next_section(self):
        self._current_section = self.headers.pop(0)
        self.keys_left.pop(0)


    def add_card(self, term: str, definition: list = []):
        if not definition:
            self.cards[self._current_section[1]].append(term + ',' + '')
        else:
            definition = ' '.join(definition) if len(definition) > 1 else definition[0]
            self.cards[self._current_section[1]].append(term + ',' + definition)


    def write_to_csv(self, filename:str, by_chapter:bool = True):
        if by_chapter:
            chapter_cards = []
            chapter = '1'
            for section, cards in self.cards.items():
                if section[0] == chapter:
                    chapter_cards.extend(cards)
                if section[0] != chapter or section == '6.4':
                    with open(f'{filename}_chap{chapter}.csv', 'w') as writer:
                        for card in chapter_cards:
                            writer.write(card + '\n')
                    chapter_cards = cards
                    chapter = section[0]
                
        else:
            with open(filename+'.csv', 'w') as writer:
                for _, cards in self.cards.items():
                    for card in cards:
                        writer.write(card + '\n')


def get_headers():
    # Have to use startswith, because of section 6
    sections = [
        ('• Viruses', '1.1:Given a scenario, analyze indicators of compromise and determine the type of malware'),
        ('• Social engineering', '1.2:Compare and contrast types of attacks'),
        ('• Types of actors', '1.3:Explain threat actor types and attributes.'),
        ('• Active reconnaissance', '1.4:Explain penetration testing concepts'),
        ('• Passively test security controls', '1.5:Explain vulnerability scanning concepts.'),
        ('• Race conditions', '1.6:Explain the impact associated with types of vulnerabilities.'),

        ('• Firewall', '2.1:Install and configure network components, both hardwareand software-based, to support organizational security.'),
        ('• Protocol analyzer', '2.2:Given a scenario, use appropriate software tools to assess the security posture of an organization'),
        ('• Unencrypted credentials/clear text', '2.3:Given a scenario, troubleshoot common security issues.'),
        ('• HIDS/HIPS', '2.4:Given a scenario, analyze and interpret output from security technologies.'),
        ('• Connection methods', '2.5:Given a scenario, deploy mobile devices securely'),
        ('• Protocols', '2.6:Given a scenario, implement secure protocols.'),

        ('• Industry-standard frameworks and reference architectures', '3.1:Explain use cases and purpose for frameworks, best practices and secure configuration guides.'),
        ('• Zones/topologies', '3.2:Given a scenario, implement secure network architecture concepts.'),
        ('• Hardware/firmware security', '3.3:Given a scenario, implement secure systems design'),
        ('• Sandboxing', '3.4:Explain the importance of secure staging deployment concepts.'),
        ('• SCADA/ICS', '3.5:Explain the security implications of embedded systems.'),
        ('• Development life-cycle models', '3.6:Summarize secure application development and deployment concepts.'),
        ('• Hypervisor', '3.7:Summarize cloud and virtualization concepts.'),
        ('• Automation/scripting', '3.8:Explain how resiliency and automation strategies reduce risk.'),
        ('• Lighting', '3.9:Explain the importance of physical security controls.'),

        ('• Identification, authentication, authorization and accounting (AAA)', '4.1:Compare and contrast identity and access management concepts'),
        ('• LDAP', '4.2:Given a scenario, install and configure identity and access services.'),
        ('• - Access control models', '4.3:Given a scenario, implement identity and access management controls'),
        ('• Account types', '4.4:Given a scenario, differentiate common account management practices.'),

        ('• Standard operating procedure', '5.1:Explain the importance of policies, plans and procedures related to organizational security.'),
        ('• RTO/RPO', '5.2:Summarize business impact analysis concepts.'),
        ('• Threat assessment', '5.3:Explain risk management processes and concepts.'),
        ('• Incident response plan', '5.4:Given a scenario, follow incident response procedures.'),
        ('• Order of volatility', '5.5:Summarize basic concepts of forensics.'),
        ('• Recovery sites', '5.6:Explain disaster recovery and continuity of operation concepts.'),
        ('• Deterrent', '5.7:Compare and contrast various types of controls.'),
        ('• Data destruction and media sanitization', '5.8:Given a scenario, carry out data security and privacy practices.'),

        ('• Symmetric algorithms', '6.1:Compare and contrast basic concepts of cryptography.'),
        ('• Symmetric algorithms_', '6.2:Explain cryptography algorithms and their basic characteristics.'),
        ('• Cryptographic protocols', '6.3:Given a scenario, install and configure wireless security settings.'),
        ('• Components', '6.4:Given a scenario, implement public key infrastructure.')
    ]
    # Thought I might use description, couldn't figure out where I wanted it
    # Leaving it out for now
    sections = [ (keyword, section.split(':')[0]) for keyword, section in sections]

    return sections


if __name__ == "__main__":
    main()