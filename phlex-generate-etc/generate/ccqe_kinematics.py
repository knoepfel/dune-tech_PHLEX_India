import math

# We'll use units of GeV for energy & momentum
# and degrees for angles

#Masses
mn = 0.939565
mp = 0.938272
mmu = 0.105658

def ccqe_kinematics(theta_mu, enu=1.0):
    thetamu = math.radians(theta_mu)

    # Derivation left as an exercise for the reader :) 
    a = 2.0 * enu * math.cos(thetamu)
    b = 2.0 * (enu + mn)
    c = mn * mn - mp * mp + mmu * mmu + 2.0 * enu * mn
    d = b * b - a * a
    emu = (b * c + a * math.sqrt(c * c - mmu * mmu * d)) / d

    pmu = math.sqrt(emu * emu - mmu * mmu)
    pmu_z = math.cos(thetamu) * pmu
    pmu_t = math.sin(thetamu) * pmu #Transverse momentum -- define this to be x-direction below

    # enu == pnu == p_proton + p_muon
    pp_z = enu - pmu_z
    ep = math.sqrt(pp_z*pp_z + pmu_t*pmu_t + mp*mp) # E = srqt(m^2 + p^2) w/ transverse momentum balance |pp_t| = |pmu_t|
    return {
        'muon': (pmu_t, 0, pmu_z, emu), # Muon 4-momentum
        'proton': (-pmu_t, 0, pp_z, ep) # Proton 4-momentum
    }

