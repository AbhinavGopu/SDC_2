class Ranker:
    def rank_candidates(self, candidates: list, user_prompt: str = "", diagnosis: str = "") -> list:
        """
        Stage 4: Cost-effectiveness and keyword-based ranking of candidates.
        Disambiguates location proper nouns (like 'Ameerpet flyover') from intervention intent.
        """
        lower_prompt = user_prompt.lower()
        
        is_location_flyover = any(phrase in lower_prompt for phrase in ["on the flyover", "near the flyover", "ameerpet flyover", "flyover flyover", "biodiversity flyover"])
        is_location_signal = any(phrase in lower_prompt for phrase in ["at the signal", "near the signal", "biodiversity signal", "junction signal", "metro signal"])

        def calculate_score(c):
            cost = c.get("cost_lakhs", 1.0)
            base_score = 100.0 / cost if cost > 0 else 1.0
            
            boost = 0.0
            cid = c.get("id", "").lower()
            name = c.get("name", "").lower()
            
            # 1. Boost matching diagnosed problem type (High Priority)
            if diagnosis == "waterlogging_induced" and cid == "drainage":
                boost += 500.0
            elif diagnosis == "signal_mistiming" and cid == "atsc":
                boost += 500.0
            elif diagnosis == "capacity_limited" and cid in ["widening", "flyover"]:
                boost += 500.0
                
            # 2. General keyword boosts (avoid location noun confusion)
            if cid in lower_prompt or name in lower_prompt:
                if cid == "flyover" and is_location_flyover and diagnosis != "capacity_limited":
                    pass
                elif cid == "atsc" and is_location_signal and diagnosis != "signal_mistiming":
                    pass
                else:
                    boost += 200.0
                
            # 3. Specific keyword boosts
            if "signal" in lower_prompt and cid == "atsc" and not (is_location_signal and diagnosis != "signal_mistiming"):
                boost += 150.0
            elif "widening" in lower_prompt and cid == "widening":
                boost += 150.0
            elif "flyover" in lower_prompt and cid == "flyover" and not (is_location_flyover and diagnosis != "capacity_limited"):
                boost += 150.0
            elif "drain" in lower_prompt and cid == "drainage":
                boost += 150.0
            elif "reroute" in lower_prompt and cid == "reroute":
                boost += 150.0
                
            return base_score + boost
            
        ranked = sorted(candidates, key=calculate_score, reverse=True)
        return ranked
