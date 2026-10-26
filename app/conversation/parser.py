from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
import re


@dataclass
class Turn:
    speaker: str  # "Customer" or "Agent"
    text: str
    sequence: int = 0
    timestamp: Optional[str] = None


@dataclass
class ConversationContext:
    customer_phone: Optional[str] = None
    call_id: Optional[int] = None
    call_status: Optional[str] = None
    duration_seconds: Optional[float] = None
    turns: List[Turn] = field(default_factory=list)
    customer_statements: List[str] = field(default_factory=list)
    clean_transcript: str = ""
    customer_only_text: str = ""
    raw_transcript: str = ""


class ConversationParser:
    """
    Parses OmniDimension call log data or raw transcripts into structured
    dialogue turns, isolating customer statements from AI interpretations.
    """

    @staticmethod
    def parse_call_log(call_data: Dict[str, Any]) -> ConversationContext:
        """
        Parses an OmniDimension call_log_data entry (dict).
        Prioritizes interactions[].user_query to isolate actual customer speech.
        Chronological turn order: in user_turns, user speaks before bot responds.
        """
        call_id = call_data.get("id")
        to_number = call_data.get("to_number")
        from_number = call_data.get("from_number")
        direction = call_data.get("call_direction", "outbound")
        customer_phone = to_number if direction == "outbound" else from_number

        duration = call_data.get("call_duration_in_seconds")
        call_status = call_data.get("call_status")
        raw_conversation = call_data.get("call_conversation", "")

        interactions = call_data.get("interactions", [])
        turns: List[Turn] = []
        customer_statements: List[str] = []

        if interactions:
            for item in interactions:
                seq = item.get("interaction_sequence", 0)
                ts = item.get("time_of_call")

                # In OmniDimension interactions, user_query is the caller's input
                # to which bot_response is the reaction.
                user_text = (item.get("user_query") or "").strip()
                if user_text:
                    turns.append(Turn(speaker="Customer", text=user_text, sequence=seq, timestamp=ts))
                    customer_statements.append(user_text)

                bot_text = (item.get("bot_response") or "").strip()
                if bot_text:
                    turns.append(Turn(speaker="Agent", text=bot_text, sequence=seq, timestamp=ts))

        # Fallback to parsing raw_conversation if interactions were empty
        if not turns and raw_conversation:
            return ConversationParser.parse_raw_transcript(
                raw_conversation,
                call_id=call_id,
                customer_phone=customer_phone,
                call_status=call_status,
                duration_seconds=duration,
            )

        clean_lines = [f"{t.speaker}: {t.text}" for t in turns]
        clean_transcript = "\n".join(clean_lines)
        customer_only_text = "\n".join(f"- {s}" for s in customer_statements)

        return ConversationContext(
            customer_phone=customer_phone,
            call_id=call_id,
            call_status=call_status,
            duration_seconds=duration,
            turns=turns,
            customer_statements=customer_statements,
            clean_transcript=clean_transcript,
            customer_only_text=customer_only_text,
            raw_transcript=raw_conversation,
        )

    @staticmethod
    def parse_raw_transcript(
        transcript_text: str,
        call_id: Optional[int] = None,
        customer_phone: Optional[str] = None,
        call_status: Optional[str] = None,
        duration_seconds: Optional[float] = None,
    ) -> ConversationContext:
        """
        Parses a plain-text or HTML-tagged transcript (e.g. with <br/> or LLM:/User: prefixes).
        """
        # Normalize HTML line breaks
        normalized = transcript_text.replace("<br/>", "\n").replace("<br>", "\n")
        lines = [line.strip() for line in normalized.splitlines() if line.strip()]

        turns: List[Turn] = []
        customer_statements: List[str] = []

        seq = 1
        for line in lines:
            # Match prefixes like 'LLM:', 'Agent:', 'Bot:', 'AI:'
            agent_match = re.match(r"^(?:LLM|Agent|Bot|AI):\s*(.*)$", line, re.IGNORECASE)
            # Match prefixes like 'User:', 'Customer:', 'Human:'
            user_match = re.match(r"^(?:User|Customer|Human):\s*(.*)$", line, re.IGNORECASE)

            if agent_match:
                content = agent_match.group(1).strip()
                if content:
                    turns.append(Turn(speaker="Agent", text=content, sequence=seq))
                    seq += 1
            elif user_match:
                content = user_match.group(1).strip()
                if content:
                    turns.append(Turn(speaker="Customer", text=content, sequence=seq))
                    customer_statements.append(content)
                    seq += 1
            else:
                # If no prefix, check if line continues previous speaker or is standalone
                if turns and turns[-1].speaker == "Customer":
                    turns[-1].text += f" {line}"
                    if customer_statements:
                        customer_statements[-1] += f" {line}"
                elif turns and turns[-1].speaker == "Agent":
                    turns[-1].text += f" {line}"
                else:
                    turns.append(Turn(speaker="Customer", text=line, sequence=seq))
                    customer_statements.append(line)
                    seq += 1

        clean_lines = [f"{t.speaker}: {t.text}" for t in turns]
        clean_transcript = "\n".join(clean_lines)
        customer_only_text = "\n".join(f"- {s}" for s in customer_statements)

        return ConversationContext(
            customer_phone=customer_phone,
            call_id=call_id,
            call_status=call_status,
            duration_seconds=duration_seconds,
            turns=turns,
            customer_statements=customer_statements,
            clean_transcript=clean_transcript,
            customer_only_text=customer_only_text,
            raw_transcript=transcript_text,
        )
