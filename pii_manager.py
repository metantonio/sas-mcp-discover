"""
PII Manager - Reversible Sensitive Data Pseudonymization & De-anonymization.

Features:
- Structured email pseudonymization maintaining domain consistency:
  - 1st email with domain A: 1@1.com
  - 2nd email with domain A: 2@1.com
  - 3rd email with domain B: 3@2.com
- Spanish DNI / NIE / NIF detection and pseudonymization (e.g. 00000001A, 00000002B)
- Spanish phone number detection and pseudonymization (e.g. +34 000 000 001)
- US phone number detection and pseudonymization (e.g. +1 (555) 010-0001)
- US Social Security Number (SSN) detection and pseudonymization (e.g. 900-01-0001)
- US ABA Routing Transit Number detection and pseudonymization with valid checksum (e.g. 011000015)
- Bank Account Numbers (US & International) detection and pseudonymization (e.g. 100000000001)
- Credit Card number detection and pseudonymization (e.g. 4000-0000-0000-0001)
- IBAN European bank account detection and pseudonymization (e.g. ES00 0000 0000 0000 0001)
- Bidirectional mapping vault:
  - mask(text) -> transforms sensitive data to pseudonyms
  - unmask(text) -> restores original sensitive data when LLM responds
  - serializable to JSON for persisting across session history
"""

import re
from typing import Dict, List, Tuple, Any


class PIIVault:
    """
    Session-level vault that maintains consistent pseudonym mappings.
    Can be serialized to and deserialized from JSON for conversation history.
    """

    # 1. Emails
    EMAIL_REGEX = re.compile(
        r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b'
    )

    # 2. Spanish DNI (8 digits + letter) or NIE (X/Y/Z + 7 digits + letter)
    DNI_NIE_REGEX = re.compile(
        r'\b([XYZxyz]?\d{7,8}[A-Za-z])\b'
    )

    # 3. Credit Card numbers (16 digits with optional spaces or hyphens)
    CREDIT_CARD_REGEX = re.compile(
        r'\b(?:\d{4}[ -]?){3}\d{4}\b'
    )

    # 4. IBAN (Spanish & European standard: 2 letters, 2 digits, up to 30 alphanumerics)
    IBAN_REGEX = re.compile(
        r'\b([A-Z]{2}\d{2}[ -]?(?:\d{4}[ -]?){4}\d{2,4})\b'
    )

    # 5. Spanish CCC (Código Cuenta Cliente: 20 digits: 4 entity + 4 office + 2 DC + 10 account)
    CCC_REGEX = re.compile(
        r'\b(\d{4}[ -]\d{4}[ -]\d{2}[ -]\d{10})\b'
    )

    # 6. US Social Security Number (SSN: XXX-XX-XXXX)
    SSN_REGEX = re.compile(
        r'\b(?!000|666|9\d{2})(\d{3})[-\s](?!00)(\d{2})[-\s](?!0000)(\d{4})\b'
    )
    # Labeled SSN (with or without dashes: e.g. "SSN: 123456789")
    SSN_LABELED_REGEX = re.compile(
        r'(?i)\b(?:ssn|social\s*security(?:\s*no|\s*number)?)\s*[:#]?\s*((?!000|666|9\d{2})\d{3}[-\s]?(?!00)\d{2}[-\s]?(?!0000)\d{4})\b'
    )

    # 7. US Phone Numbers: e.g. (415) 555-2671, +1-202-555-0199, 415.555.2671, 415-555-2671
    US_PHONE_REGEX = re.compile(
        r'(?:\+?1[\s.-]?)?(?:\([2-9]\d{2}\)|[2-9]\d{2})[\s.-][2-9]\d{2}[\s.-]\d{4}\b'
    )

    # 8. Spanish Phone numbers (9 digits starting with 6, 7, 8, 9, optional +34 prefix)
    PHONE_ES_REGEX = re.compile(
        r'(?:\+?34[\s-]?)?(?:\(?\d{2,3}\)?[\s-]?)?(?:[6789]\d{2}[\s-]?\d{3}[\s-]?\d{3}|[6789]\d{8})\b'
    )

    # 9. US ABA Routing Transit Numbers (labeled: e.g. "Routing: 021000021", "ABA # 123456789", "RTN: ...")
    ROUTING_LABELED_REGEX = re.compile(
        r'(?i)\b(?:routing(?:\s*(?:transit)?\s*(?:number|no|#))?|aba(?:\s*#)?|rtn)\s*[:#]?\s*(\d{9})\b'
    )

    # 10. Bank Account Numbers (labeled: e.g. "Account Number: 123456789012", "Cuenta: 1234567890")
    ACCOUNT_LABELED_REGEX = re.compile(
        r'(?i)\b(?:account(?:\s*(?:number|no|#))?|cuenta(?:\s*(?:bancaria|corriente|ahorros|de\s*ahorros|no|#))?|acct|cta|no\.\s*cta|nº\s*cuenta)\s*[:#]?\s*([0-9]{8,17})\b'
    )

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all counters and mappings."""
        # Domain string -> domain_id (1, 2, ...)
        self.domains: Dict[str, int] = {}
        self.domain_counter: int = 0

        # Global email counter (1, 2, ...)
        self.email_counter: int = 0

        # Category counters
        self.dni_counter: int = 0
        self.phone_counter: int = 0
        self.us_phone_counter: int = 0
        self.ssn_counter: int = 0
        self.routing_counter: int = 0
        self.bank_account_counter: int = 0
        self.card_counter: int = 0
        self.iban_counter: int = 0

        # Bi-directional mappings
        # real_value_normalized -> mask
        self.real_to_mask: Dict[str, str] = {}
        # mask -> original_value (preserving exact casing)
        self.mask_to_real: Dict[str, str] = {}

        # Audit log of substitutions performed
        self.audit_log: List[Dict[str, str]] = []

    def to_dict(self) -> Dict[str, Any]:
        """Serialize vault state to dict for session saving."""
        return {
            "domains": self.domains,
            "domain_counter": self.domain_counter,
            "email_counter": self.email_counter,
            "dni_counter": self.dni_counter,
            "phone_counter": self.phone_counter,
            "us_phone_counter": self.us_phone_counter,
            "ssn_counter": self.ssn_counter,
            "routing_counter": self.routing_counter,
            "bank_account_counter": self.bank_account_counter,
            "card_counter": self.card_counter,
            "iban_counter": self.iban_counter,
            "real_to_mask": self.real_to_mask,
            "mask_to_real": self.mask_to_real,
            "audit_log": self.audit_log,
        }

    def from_dict(self, data: Dict[str, Any]):
        """Restore vault state from saved session dict."""
        if not data:
            self.reset()
            return
        self.domains = data.get("domains", {})
        self.domain_counter = data.get("domain_counter", 0)
        self.email_counter = data.get("email_counter", 0)
        self.dni_counter = data.get("dni_counter", 0)
        self.phone_counter = data.get("phone_counter", 0)
        self.us_phone_counter = data.get("us_phone_counter", 0)
        self.ssn_counter = data.get("ssn_counter", 0)
        self.routing_counter = data.get("routing_counter", 0)
        self.bank_account_counter = data.get("bank_account_counter", 0)
        self.card_counter = data.get("card_counter", 0)
        self.iban_counter = data.get("iban_counter", 0)
        self.real_to_mask = data.get("real_to_mask", {})
        self.mask_to_real = data.get("mask_to_real", {})
        self.audit_log = data.get("audit_log", [])

    # ------------------------------------------------------------------
    # Helper: ABA Routing Checksum
    # ------------------------------------------------------------------
    @staticmethod
    def _is_valid_aba(num_str: str) -> bool:
        """Verify ABA Routing Transit Number checksum."""
        if len(num_str) != 9 or not num_str.isdigit():
            return False
        d = [int(c) for c in num_str]
        chk = (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + 1 * (d[2] + d[5] + d[8])) % 10
        return chk == 0

    # ------------------------------------------------------------------
    # Pseudonym generators
    # ------------------------------------------------------------------
    def _mask_email(self, full_email: str, domain_part: str) -> str:
        norm_email = full_email.strip().lower()
        if norm_email in self.real_to_mask:
            return self.real_to_mask[norm_email]

        norm_domain = domain_part.strip().lower()
        if norm_domain not in self.domains:
            self.domain_counter += 1
            self.domains[norm_domain] = self.domain_counter
        domain_id = self.domains[norm_domain]

        self.email_counter += 1
        pseudo = f"{self.email_counter}@{domain_id}.com"

        self.real_to_mask[norm_email] = pseudo
        self.mask_to_real[pseudo] = full_email.strip()
        self.audit_log.append({
            "type": "email",
            "original": full_email.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_dni(self, raw_dni: str) -> str:
        clean = raw_dni.strip().upper()
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.dni_counter += 1
        letter = chr(ord('A') + ((self.dni_counter - 1) % 26))
        pseudo = f"{self.dni_counter:08d}{letter}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_dni.strip()
        self.audit_log.append({
            "type": "dni_nie",
            "original": raw_dni.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_phone(self, raw_phone: str) -> str:
        clean = re.sub(r'[\s\-()]', '', raw_phone.strip())
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.phone_counter += 1
        pseudo = f"+34 000 000 {self.phone_counter:03d}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_phone.strip()
        self.audit_log.append({
            "type": "phone_es",
            "original": raw_phone.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_us_phone(self, raw_phone: str) -> str:
        clean = re.sub(r'[\s\-().+]', '', raw_phone.strip())
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.us_phone_counter += 1
        # NANPA reserved fictitious range: (555) 0100 to 0199
        sub_id = (self.us_phone_counter - 1) % 100
        has_prefix = raw_phone.strip().startswith("+1") or raw_phone.strip().startswith("1")
        pseudo = f"+1 (555) 010-{sub_id:04d}" if has_prefix else f"(555) 010-{sub_id:04d}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_phone.strip()
        self.audit_log.append({
            "type": "phone_us",
            "original": raw_phone.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_ssn(self, raw_ssn: str) -> str:
        clean = re.sub(r'[\s\-]', '', raw_ssn.strip())
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.ssn_counter += 1
        # 900-series numbers are SSA-reserved fictitious SSNs that will never be issued
        pseudo = f"900-{self.ssn_counter:02d}-{self.ssn_counter:04d}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_ssn.strip()
        self.audit_log.append({
            "type": "ssn_us",
            "original": raw_ssn.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_routing(self, raw_routing: str) -> str:
        clean = re.sub(r'[\s\-]', '', raw_routing.strip())
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.routing_counter += 1
        # Generate valid 9-digit dummy ABA routing number with correct check digit
        base = f"01100{self.routing_counter:03d}"
        d = [int(c) for c in base]
        chk = (10 - ((3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + 1 * (d[2] + d[5])) % 10)) % 10
        pseudo = f"{base}{chk}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_routing.strip()
        self.audit_log.append({
            "type": "routing_number",
            "original": raw_routing.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_bank_account(self, raw_account: str) -> str:
        clean = re.sub(r'[\s\-]', '', raw_account.strip())
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.bank_account_counter += 1
        # 12-digit dummy numeric account number
        pseudo = f"100000{self.bank_account_counter:06d}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_account.strip()
        self.audit_log.append({
            "type": "bank_account",
            "original": raw_account.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_card(self, raw_card: str) -> str:
        clean = re.sub(r'[\s\-]', '', raw_card.strip())
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.card_counter += 1
        pseudo = f"4000-0000-0000-{self.card_counter:04d}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_card.strip()
        self.audit_log.append({
            "type": "credit_card",
            "original": raw_card.strip(),
            "masked": pseudo,
        })
        return pseudo

    def _mask_iban(self, raw_iban: str) -> str:
        clean = re.sub(r'[\s\-]', '', raw_iban.strip()).upper()
        if clean in self.real_to_mask:
            return self.real_to_mask[clean]

        self.iban_counter += 1
        pseudo = f"ES00 0000 0000 0000 {self.iban_counter:04d}"

        self.real_to_mask[clean] = pseudo
        self.mask_to_real[pseudo] = raw_iban.strip()
        self.audit_log.append({
            "type": "iban",
            "original": raw_iban.strip(),
            "masked": pseudo,
        })
        return pseudo

    # ------------------------------------------------------------------
    # Main Public API: Mask and Unmask
    # ------------------------------------------------------------------
    def mask_text(self, text: str) -> Tuple[str, List[Dict[str, str]]]:
        """
        Mask all PII in `text` using unified single-pass match resolution.
        Avoids cross-pattern collision and eliminates risk of sub-matching within pseudonyms.
        Returns:
            (masked_text, newly_masked_items)
        """
        if not text:
            return text, []

        start_count = len(self.audit_log)
        matches = []

        # 1. IBAN (European)
        for m in self.IBAN_REGEX.finditer(text):
            matches.append((m.start(1), m.end(1), "iban", m.group(1)))

        # 2. Spanish CCC Bank Account (20 digits)
        for m in self.CCC_REGEX.finditer(text):
            matches.append((m.start(1), m.end(1), "bank_account", m.group(1)))

        # 3. Credit Card (16 digits)
        for m in self.CREDIT_CARD_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "card", m.group(0)))

        # 4. Emails
        for m in self.EMAIL_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "email", (m.group(0), m.group(1))))

        # 5. US Social Security Numbers (labeled and standalone XXX-XX-XXXX)
        for m in self.SSN_LABELED_REGEX.finditer(text):
            matches.append((m.start(1), m.end(1), "ssn", m.group(1)))
        for m in self.SSN_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "ssn", m.group(0)))

        # 6. US Routing Numbers (labeled)
        for m in self.ROUTING_LABELED_REGEX.finditer(text):
            matches.append((m.start(1), m.end(1), "routing", m.group(1)))

        # 7. Bank Account Numbers (labeled)
        for m in self.ACCOUNT_LABELED_REGEX.finditer(text):
            matches.append((m.start(1), m.end(1), "bank_account", m.group(1)))

        # 8. US Phone Numbers
        for m in self.US_PHONE_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "us_phone", m.group(0)))

        # 9. Spanish DNI / NIE
        for m in self.DNI_NIE_REGEX.finditer(text):
            matches.append((m.start(1), m.end(1), "dni", m.group(1)))

        # 10. Spanish Phone Numbers
        for m in self.PHONE_ES_REGEX.finditer(text):
            matches.append((m.start(), m.end(), "phone_es", m.group(0)))

        # 11. Standalone 9-digit ABA Routing numbers (checksum validated)
        for m in re.finditer(r'\b\d{9}\b', text):
            cand = m.group(0)
            if self._is_valid_aba(cand):
                matches.append((m.start(), m.end(), "routing", cand))

        # Sort matches by start position; for ties, prefer longer match
        matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

        # Filter out overlapping matches (greedy non-overlapping interval selection)
        non_overlapping = []
        last_end = 0
        for start, end, mtype, val in matches:
            if start >= last_end:
                non_overlapping.append((start, end, mtype, val))
                last_end = end

        # Pre-generate replacements in natural left-to-right reading order
        # to ensure sequential IDs (1@1.com, 2@1.com, etc.) match text flow.
        replacements = []
        for start, end, mtype, val in non_overlapping:
            if mtype == "iban":
                rep = self._mask_iban(val)
            elif mtype == "card":
                rep = self._mask_card(val)
            elif mtype == "email":
                rep = self._mask_email(val[0], val[1])
            elif mtype == "ssn":
                rep = self._mask_ssn(val)
            elif mtype == "routing":
                rep = self._mask_routing(val)
            elif mtype == "bank_account":
                rep = self._mask_bank_account(val)
            elif mtype == "us_phone":
                rep = self._mask_us_phone(val)
            elif mtype == "dni":
                rep = self._mask_dni(val)
            elif mtype == "phone_es":
                rep = self._mask_phone(val)
            else:
                rep = val
            replacements.append((start, end, rep))

        # Replace from right to left so original slice indices remain accurate
        result = list(text)
        for start, end, rep in reversed(replacements):
            result[start:end] = list(rep)

        masked_text = "".join(result)
        newly_masked = self.audit_log[start_count:]
        return masked_text, newly_masked

    def unmask_text(self, text: str) -> str:
        """
        Replace all pseudonyms in `text` with their original values.
        Sorts keys by length descending to avoid partial prefix collisions.
        """
        if not text or not self.mask_to_real:
            return text

        sorted_masks = sorted(self.mask_to_real.keys(), key=len, reverse=True)
        for mask in sorted_masks:
            original = self.mask_to_real[mask]
            text = text.replace(mask, original)

        return text

    def get_summary_text(self) -> str:
        """Human-readable summary of protected items in this session."""
        if not self.mask_to_real:
            return "No sensitive PII has been detected in this session."

        lines = [f"Total protected items: {len(self.mask_to_real)}"]
        by_type = {}
        for entry in self.audit_log:
            by_type.setdefault(entry["type"], []).append(f"{entry['original']} ➔ {entry['masked']}")

        for cat, items in by_type.items():
            lines.append(f"\n[{cat.upper()}]:")
            for item in items:
                lines.append(f"  • {item}")
        return "\n".join(lines)
