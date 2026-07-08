class RecommendationService:
    @staticmethod
    def generate_recommendation(
        pc_id: str,
        complaint: str,
        fused_problem: str,
        health_score: float,
        failure_risk: float,
        rul_days: int,
        anomaly_label: str,
        sensors: dict,
        engineered_features: dict,
        similar_cases: list
    ) -> dict:
        """
        Synthesizes an offline, evidence-based maintenance recommendation.
        Merges predictions, sensor readings, and historical treatments.
        """
        evidence_ids = [str(case["repair_id"]) for case in similar_cases]
        
        # 1. Primary Recommendation based on Fused Problem Assessment
        primary_rec = ""
        diagnostic_seq = []
        immediate_acts = []
        preventive_acts = []
        monitoring_acts = []
        likely_causes = []
        escalations = []
        
        # Extract top diagnostics/treatments from historical matches
        hist_treatments = [case["treatment_taken"] for case in similar_cases if case["treatment_taken"]]
        hist_diagnoses = [case["confirmed_diagnosis"] for case in similar_cases if case["confirmed_diagnosis"]]
        
        if fused_problem == "Overheating":
            primary_rec = "Perform physical inspection of the cooling assembly. Check fan rotation, clear heat sinks, and refresh thermal interface paste."
            
            diagnostic_seq = [
                "Verify cooling fan operation by listening for noise or assessing RPM levels.",
                "Inspect air exhaust and intake ports for dust blockage.",
                "Remove bottom case and check heatsink-to-processor contact.",
                "If temperatures remain high after cleaning, replace the thermal paste."
            ]
            
            immediate_acts = [
                "Clear airflow obstructions from the laptop ventilation channels.",
                "Verify fan RPM is adjusting dynamically under high CPU load."
            ]
            
            preventive_acts = [
                "Schedule physical cleaning of internal components every 6 months in dusty environments.",
                "Configure BIOS settings to optimize cooling fan profiles for sustained workloads."
            ]
            
            monitoring_acts = [
                "Configure continuous temperature monitoring log. Raise warning above 80°C.",
                "Log Fan Speed anomalies relative to core processor load."
            ]
            
            likely_causes = [
                "Internal cooling fan dust occlusion (referenced in historical repairs)",
                "Crystallized or degraded thermal interface material",
                "Worn-out fan rotor bearing reducing cooling capacity"
            ]
            
            escalations = [
                "CPU temperature exceeds 95°C for more than 5 minutes.",
                "Thermal throttling causes automatic system shutdown during routine tasks."
            ]
            
        elif fused_problem == "Memory Leak":
            primary_rec = "Examine running processes for memory leak. Review background agents, telemetry services, and recently updated software."
            
            diagnostic_seq = [
                "Monitor RAM usage over 2 hours of normal work to identify memory growth.",
                "Filter running tasks by private working set size to locate leaking processes.",
                "Review event logs for Out of Memory warnings or system resource faults."
            ]
            
            immediate_acts = [
                "Restart the identified service or process causing RAM accumulation.",
                "Apply software updates or roll back the leaking system monitoring agent."
            ]
            
            preventive_acts = [
                "Deploy automatic limits on heap memory size for custom background scripts.",
                "Add scheduled daily restarts for devices running legacy services."
            ]
            
            monitoring_acts = [
                "Track RAM consumption trend over time.",
                "Set alerts when memory usage exceeds 90% when no active applications are running."
            ]
            
            likely_causes = [
                "Background telemetry script failing to release memory handles (common match)",
                "Leaking browser extension or persistent client side daemon",
                "Operating system network driver memory retention"
            ]
            
            escalations = [
                "Memory consumption exceeds 95% causing system freeze.",
                "Critical system services crash due to memory allocation failure."
            ]
            
        elif fused_problem == "Disk Failure":
            primary_rec = "Perform storage drive health audit. Backup user profile data immediately and replace degraded storage drive if sector faults exist."
            
            diagnostic_seq = [
                "Run SMART diagnostics on SSD/HDD drive to verify block wear and sector integrity.",
                "Check system logs for NTFS/Disk read/write failure errors.",
                "Reseat SATA/NVMe cable connection internally to eliminate socket wear."
            ]
            
            immediate_acts = [
                "Initiate full database/user profile file backup to secure local drive data.",
                "Run standard disk check utility (chkdsk) to patch file system errors."
            ]
            
            preventive_acts = [
                "Replace mechanical hard drives with high-end SSDs for durability.",
                "Configure automatic daily server backups for files in active directories."
            ]
            
            monitoring_acts = [
                "Monitor disk write latency times and read failure rates.",
                "Verify SSD health indicators (Total Bytes Written limit remaining)."
            ]
            
            likely_causes = [
                "Physical bad sector degradation on magnetic disk",
                "Write endurance limit reached on SSD storage controller",
                "Filesystem journal corruption following improper power off"
            ]
            
            escalations = [
                "SMART health assessment returns 'Fail' state.",
                "Device fails to boot, showing 'No bootable device found'."
            ]
            
        elif fused_problem == "Power Issue":
            primary_rec = "Audit input charging voltage and inspect physical battery health for thermal swelling or cell degradation."
            
            diagnostic_seq = [
                "Measure charger output voltage under load to check for fluctuation.",
                "Run system diagnostic report to evaluate remaining battery charge cycles.",
                "Inspect charging jack and DC power socket pins for cracking or wear."
            ]
            
            immediate_acts = [
                "Test system with a verified nominal power adapter charger.",
                "Remove swollen batteries immediately to prevent structural chassis damage."
            ]
            
            preventive_acts = [
                "Ensure power is supplied through standard surge protection strips.",
                "Decommission batteries once wear exceeds 75% capacity limits."
            ]
            
            monitoring_acts = [
                "Log input power rail voltage stability metrics.",
                "Track battery discharge rate changes over time."
            ]
            
            likely_causes = [
                "Internal lithium cell degradation (end of charge cycles)",
                "Damaged charger adapter cable causing voltage drops",
                "Motherboard DC charging jack solder connection fracture"
            ]
            
            escalations = [
                "Battery charges intermittently or is swollen.",
                "Motherboard power rail voltage fluctuates below 11V or above 19V."
            ]
            
        else: # No Problem
            primary_rec = "Routine system operational compliance check. Run standard diagnostics and ensure security updates are complete."
            
            diagnostic_seq = [
                "Inspect system logs for minor device driver warnings.",
                "Run basic hardware diagnostic tests (CPU, RAM, Hard drive)."
            ]
            
            immediate_acts = [
                "Clean keyboard keycaps, cooling exhaust ports, and chassis exterior."
            ]
            
            preventive_acts = [
                "Keep operating system security patches and antivirus definition libraries current."
            ]
            
            monitoring_acts = [
                "Verify telemetry collection agent is reporting metrics successfully."
            ]
            
            likely_causes = [
                "Normal wear, scheduled maintenance inspection"
            ]
            
            escalations = [
                "Any hardware sensor exceeds warning thresholds during diagnostic run."
            ]

        # Inject historical treatment notes as evidence details
        if hist_treatments:
            diagnostic_seq.append(f"Refer to historical repairs: {', '.join(evidence_ids)} for treatment patterns.")

        return {
            "primary_recommendation": primary_rec,
            "diagnostic_sequence": diagnostic_seq,
            "immediate_actions": immediate_acts,
            "preventive_actions": preventive_acts,
            "monitoring_actions": monitoring_acts,
            "likely_root_causes": likely_causes,
            "evidence_used": evidence_ids,
            "escalation_conditions": escalations
        }
