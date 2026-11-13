; name: test_boot_poke
; default: no
; site: $86a8
; Loader self-test (boot phase): "Please dont hurt me soldier" -> upper case "PLEASE" in the resident game text.
; RAM proof only (rarely shown message): peek $86a8 after boot == 504c45415345.
        org     $86a8
        dc.b    "PLEASE"
