"""Core calculations for the optical fiber link simulator."""

from dataclasses import dataclass
from math import sqrt


SPEED_OF_LIGHT_M_S = 3e8
NB_CONNECTORS_DEFAULT = 2
FIBER_LIBRARY = {
    "SMF (Monomode)": {
        "alpha_typique": 0.2,
        "Dc": 17.0,
        "modal": False,
        "n_c": 1.468,
        "Delta": 0.0,
    },
    "FGI (Gradient)": {
        "alpha_typique": 0.5,
        "Dc": 0.0,
        "modal": True,
        "n_c": 1.48,
        "Delta": 0.01,
    },
}


@dataclass
class SimulationInputs:
    """Input parameters provided by the user."""

    wavelength_nm: float
    spectral_width_nm: float
    emitted_power_dbm: float
    fiber_type: str
    attenuation_db_per_km: float
    chromatic_dispersion_ps_nm_km: float
    length_km: float
    receiver_sensitivity_dbm: float
    spool_length_km: float
    splice_loss_db: float
    connector_loss_db: float
    safety_margin_db: float
    required_bitrate_gbps: float
    line_code: str
    line_code_coeff: float
    core_index_nc: float
    delta_rel_index: float
    nb_connectors: int = NB_CONNECTORS_DEFAULT


@dataclass
class SimulationResults:
    """Computed metrics returned by the simulator."""

    received_power_dbm: float
    computed_margin_db: float
    is_link_functional: bool
    verdict_message: str
    maximum_distance_km: float
    maximum_bit_rate_gbps: float
    total_dispersion_ps: float
    chromatic_dispersion_ps: float
    modal_dispersion_ps: float
    fiber_loss_db: float
    splice_loss_total_db: float
    connector_loss_total_db: float
    number_of_splices: int


class OpticalLinkCalculator:
    """Calculation helper class with course-aligned formulas."""

    @staticmethod
    def splice_count(length_km: float, spool_length_km: float) -> int:
        if spool_length_km <= 0:
            return 0
        return max(0, int(length_km / spool_length_km) - 1)

    @staticmethod
    def maximum_distance(
        emitted_power_dbm: float,
        sensitivity_dbm: float,
        attenuation_db_per_km: float,
        splice_loss_db: float,
        connector_loss_db: float,
        safety_margin_db: float,
        spool_length_km: float,
        nb_connectors: int,
    ) -> float:
        # Conservative closed-form estimate using power budget losses:
        # Pr >= S + marge  => alpha*L + losses <= Pe - S - marge
        # Splices approximated with one splice per spool length.
        if attenuation_db_per_km <= 0:
            return 0.0
        budget_db = emitted_power_dbm - sensitivity_dbm - safety_margin_db
        fixed_losses_db = nb_connectors * connector_loss_db
        if budget_db <= fixed_losses_db:
            return 0.0

        splice_density = (splice_loss_db / spool_length_km) if spool_length_km > 0 else 0.0
        effective_alpha = attenuation_db_per_km + splice_density
        if effective_alpha <= 0:
            return 0.0
        return max(0.0, (budget_db - fixed_losses_db) / effective_alpha)

    @staticmethod
    def bitrate_max_gbps(total_dispersion_ps: float, line_code_coeff: float) -> float:
        # Bmax = coeff_code / delta_tau
        if total_dispersion_ps <= 0:
            return 1000.0
        return line_code_coeff / (total_dispersion_ps * 1e-12) / 1e9

    @classmethod
    def power_components(
        cls,
        data: SimulationInputs,
    ) -> tuple[float, float, float, int, float]:
        fiber_loss_db = data.attenuation_db_per_km * data.length_km
        number_of_splices = cls.splice_count(data.length_km, data.spool_length_km)
        splice_loss_total_db = number_of_splices * data.splice_loss_db
        connector_loss_total_db = data.nb_connectors * data.connector_loss_db
        received_power_dbm = (
            data.emitted_power_dbm
            - fiber_loss_db
            - splice_loss_total_db
            - connector_loss_total_db
        )
        return (
            received_power_dbm,
            fiber_loss_db,
            splice_loss_total_db,
            number_of_splices,
            connector_loss_total_db,
        )

    @staticmethod
    def dispersion_components(data: SimulationInputs) -> tuple[float, float, float]:
        chromatic_ps = abs(data.chromatic_dispersion_ps_nm_km) * data.spectral_width_nm * data.length_km
        modal_ps = 0.0
        profile = FIBER_LIBRARY.get(data.fiber_type, {})
        is_modal = bool(profile.get("modal", False))
        if is_modal:
            length_m = data.length_km * 1000.0
            modal_ps = (
                (data.core_index_nc / (8.0 * SPEED_OF_LIGHT_M_S))
                * (data.delta_rel_index**2)
                * length_m
                * 1e12
            )
        total_ps = sqrt(chromatic_ps**2 + modal_ps**2)
        return total_ps, chromatic_ps, modal_ps

    @staticmethod
    def verdict(
        computed_margin_db: float,
        safety_margin_db: float,
        max_bitrate_gbps: float,
        required_bitrate_gbps: float,
        line_code: str,
    ) -> tuple[bool, str]:
        if computed_margin_db < safety_margin_db:
            return (
                False,
                f"Marge insuffisante ({computed_margin_db:.2f} < {safety_margin_db:.2f} dB requis)",
            )
        if max_bitrate_gbps < required_bitrate_gbps:
            return (
                False,
                f"Debit max insuffisant avec {line_code} ({max_bitrate_gbps:.2f} < {required_bitrate_gbps:.3f} Gbps)",
            )
        return True, "Liaison fonctionnelle"

    @classmethod
    def run_simulation(cls, data: SimulationInputs) -> SimulationResults:
        (
            pr,
            fiber_loss_db,
            splice_loss_total_db,
            number_of_splices,
            connector_loss_total_db,
        ) = cls.power_components(data)
        computed_margin_db = pr - data.receiver_sensitivity_dbm
        total_dispersion_ps, chromatic_ps, modal_ps = cls.dispersion_components(data)
        bmax = cls.bitrate_max_gbps(total_dispersion_ps, data.line_code_coeff)
        link_ok, verdict_message = cls.verdict(
            computed_margin_db=computed_margin_db,
            safety_margin_db=data.safety_margin_db,
            max_bitrate_gbps=bmax,
            required_bitrate_gbps=data.required_bitrate_gbps,
            line_code=data.line_code,
        )
        lmax = cls.maximum_distance(
            emitted_power_dbm=data.emitted_power_dbm,
            sensitivity_dbm=data.receiver_sensitivity_dbm,
            attenuation_db_per_km=data.attenuation_db_per_km,
            splice_loss_db=data.splice_loss_db,
            connector_loss_db=data.connector_loss_db,
            safety_margin_db=data.safety_margin_db,
            spool_length_km=data.spool_length_km,
            nb_connectors=data.nb_connectors,
        )

        return SimulationResults(
            received_power_dbm=pr,
            computed_margin_db=computed_margin_db,
            is_link_functional=link_ok,
            verdict_message=verdict_message,
            maximum_distance_km=lmax,
            maximum_bit_rate_gbps=bmax,
            total_dispersion_ps=total_dispersion_ps,
            chromatic_dispersion_ps=chromatic_ps,
            modal_dispersion_ps=modal_ps,
            fiber_loss_db=fiber_loss_db,
            splice_loss_total_db=splice_loss_total_db,
            connector_loss_total_db=connector_loss_total_db,
            number_of_splices=number_of_splices,
        )
