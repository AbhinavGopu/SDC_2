class ProblemDiagnoser:
    def diagnose_problem(self, congestion_index: float, complaints: list, geography: dict = None) -> str:
        """
        Stage 1: Diagnose problem type
        - recurring_peak: default/high congestion
        - capacity_limited: narrow lanes / high office density
        - waterlogging_induced: keywords relating to flooding
        - signal_mistiming: signal queues
        - one_off: incident/construction
        """
        complaint_texts = []
        for c in complaints:
            if hasattr(c, "description"):
                desc = c.description or ""
            elif isinstance(c, dict):
                desc = c.get("description", "")
            else:
                desc = str(c)
            complaint_texts.append(desc.lower())
            
        combined_text = " ".join(complaint_texts)
        
        if any(w in combined_text for w in ["waterlog", "flood", "drain", "rain", "sewage", "water"]):
            return "waterlogging_induced"
        if any(w in combined_text for w in ["signal", "timing", "atsc", "cycle"]):
            return "signal_mistiming"
        if any(w in combined_text for w in ["widening", "narrow", "lane", "flyover", "capacity"]):
            return "capacity_limited"
        if any(w in combined_text for w in ["accident", "construction", "one-off", "incident", "blocked"]):
            return "one_off"
            
        if congestion_index > 80.0:
            return "capacity_limited"
            
        return "recurring_peak"
