from pinner.packageset import Packageset

NIXENV_P_1 = """\
nixpkgs.accounts-qt                                                      accounts-qt-1.15
nixpkgs.libsForQt5.accounts-qt                                           accounts-qt-1.15
nixpkgs.accountsservice                                                  accountsservice-0.6.55
nixpkgs.acct                                                             acct-6.6.4
nixpkgs.acd-cli                                                          acd_cli-0.3.2
nixpkgs.acl2                                                             acl2-8.2
nixpkgs.acme-client                                                      acme-client-0.1.16
nixpkgs.acme-sh                                                          acme.sh-2.8.3
nixpkgs.acpi                                                             acpi-1.7
nixpkgs.linuxPackages_4_14.acpi_call                                     acpi-call-4.14.164
nixpkgs.linuxPackages.acpi_call                                          acpi-call-4.19.95
nixpkgs.linuxPackages-libre.acpi_call                                    acpi-call-4.19.95
"""

# changed versions for accounts-qt-1.16 and acl2; removed acme.sh; added acpid
NIXENV_P_2 = """\
nixpkgs.accounts-qt                                                      accounts-qt-1.15
nixpkgs.libsForQt5.accounts-qt                                           accounts-qt-1.16
nixpkgs.accountsservice                                                  accountsservice-0.6.55
nixpkgs.acct                                                             acct-6.6.4
nixpkgs.acd-cli                                                          acd_cli-0.3.2
nixpkgs.acl2                                                             acl2-9.1
nixpkgs.acme-client                                                      acme-client-0.1.16
nixpkgs.acpi                                                             acpi-1.7
nixpkgs.linuxPackages_4_14.acpi_call                                     acpi-call-4.14.164
nixpkgs.linuxPackages.acpi_call                                          acpi-call-4.19.95
nixpkgs.linuxPackages-libre.acpi_call                                    acpi-call-4.19.95
nixpkgs.acpid                                                            acpid-2.0.32
"""


def test_parse():
    ps = Packageset.parse(NIXENV_P_1)
    assert ps.pkgs == {
        'nixpkgs.accounts-qt': ('accounts-qt', '1.15'),
        'nixpkgs.libsForQt5.accounts-qt': ('accounts-qt', '1.15'),
        'nixpkgs.accountsservice': ('accountsservice', '0.6.55'),
        'nixpkgs.acct': ('acct', '6.6.4'),
        'nixpkgs.acd-cli': ('acd_cli', '0.3.2'),
        'nixpkgs.acl2': ('acl2', '8.2'),
        'nixpkgs.acme-client': ('acme-client', '0.1.16'),
        'nixpkgs.acme-sh': ('acme.sh', '2.8.3'),
        'nixpkgs.acpi': ('acpi', '1.7'),
        'nixpkgs.linuxPackages_4_14.acpi_call': ('acpi-call', '4.14.164'),
        'nixpkgs.linuxPackages.acpi_call': ('acpi-call', '4.19.95'),
        'nixpkgs.linuxPackages-libre.acpi_call': ('acpi-call', '4.19.95'),
    }


def test_diff():
    ps1 = Packageset.parse(NIXENV_P_1)
    ps2 = Packageset.parse(NIXENV_P_2)
    assert ps1.diff(ps2) == {
        'updated': {
            'nixpkgs.libsForQt5.accounts-qt':
                'accounts-qt-1.15 -> accounts-qt-1.16',
            'nixpkgs.acl2': 'acl2-8.2 -> acl2-9.1'
        },
        'added': {'nixpkgs.acme-sh': 'acme.sh-2.8.3'},
        'removed': {'nixpkgs.acpid': 'acpid-2.0.32'}
    }
