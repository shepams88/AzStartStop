import azure.functions as func
from azure.mgmt.compute import ComputeManagementClient
from azure.identity import DefaultAzureCredential
import logging
import utilities

startstop_bp = func.Blueprint()

@startstop_bp.function_name(name="StartStop")
@startstop_bp.route(route="startstop", methods=["POST"])
def start_stop_vms(req: func.HttpRequest) -> func.HttpResponse:
    vm_name = req.params.get('vm_name')
    if not vm_name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            vm_name = req_body.get('vm_name')

    if not vm_name:
        return func.HttpResponse(
            "Please pass the VM name in the request body",
            status_code=400
        )

    # Get the set timezone
    current_timezone = utilities.get_setting("Timezone")
    if not current_timezone:
        # Default to UTC if the user hasn't set a timezone
        current_timezone = "UTC"
    current_time = datetime.datetime.now(pytz.timezone(current_timezone))
    logging.info(f"Evaluating start/stop at {current_time}")

    for subscription in utilities.get_subscriptions():
        logging.info(f"Processing subscription: {subscription['id']}")
        compute_client = ComputeManagementClient(
            credential=DefaultAzureCredential(exclude_environment_credential=True), 
            subscription_id=subscription["id"]
        )

        for vm in compute_client.virtual_machines.list_all():
            if vm.name == vm_name:
                logging.info(f"Found VM: {vm.id}")
                vm_state = utilities.extract_vm_state(vm, compute_client)
                logging.info(f"[{vm.name}]: {vm_state}")

                if vm_state != "running":
                    utilities.log_vm_event(vm, "starting")
                    utilities.set_vm_state('started', vm, compute_client)
                    logging.info(f"[{vm.name}]: starting...")
                    return func.HttpResponse(f"VM {vm_name} is starting.", status_code=200)
                else:
                    return func.HttpResponse(f"VM {vm_name} is already running.", status_code=200)

    return func.HttpResponse(f"VM {vm_name} not found.", status_code=404)
